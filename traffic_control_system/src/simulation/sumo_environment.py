"""
SUMO-based Traffic Simulation Environment
Integrates with SUMO traffic simulator for realistic traffic modeling
"""

import os
import sys
import subprocess
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import logging
import time
from pathlib import Path
import tempfile
import json

# Try to import SUMO libraries
try:
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.path.append('/usr/share/sumo/tools')  # Default Ubuntu installation
    
    import traci
    import sumolib
    SUMO_AVAILABLE = True
except ImportError:
    SUMO_AVAILABLE = False
    logging.warning("SUMO not available. Using simulation fallback.")

logger = logging.getLogger(__name__)


class SUMOTrafficSimulation:
    """
    SUMO-based Traffic Simulation Environment
    
    Features:
    - Realistic traffic flow modeling
    - Multiple intersection scenarios
    - Emergency vehicle simulation
    - Weather and time-of-day effects
    - Integration with DRL agent
    """
    
    def __init__(
        self,
        network_file: Optional[str] = None,
        route_file: Optional[str] = None,
        config_file: Optional[str] = None,
        gui: bool = False,
        step_length: float = 1.0,
        simulation_time: int = 3600
    ):
        """
        Initialize SUMO simulation
        
        Args:
            network_file: Path to SUMO network file (.net.xml)
            route_file: Path to SUMO route file (.rou.xml)
            config_file: Path to SUMO config file (.sumocfg)
            gui: Whether to use SUMO GUI
            step_length: Simulation step length in seconds
            simulation_time: Total simulation time in seconds
        """
        self.network_file = network_file
        self.route_file = route_file
        self.config_file = config_file
        self.gui = gui
        self.step_length = step_length
        self.simulation_time = simulation_time
        
        # Simulation state
        self.current_time = 0
        self.is_running = False
        self.connection_label = f"sumo_{int(time.time())}"
        
        # Traffic light control
        self.traffic_lights = {}
        self.intersection_data = {}
        
        # Performance metrics
        self.metrics = {
            'total_vehicles': 0,
            'completed_trips': 0,
            'total_waiting_time': 0,
            'average_speed': 0,
            'emissions': {'co2': 0, 'co': 0, 'nox': 0, 'pmx': 0}
        }
        
        # Create default network if none provided
        if not network_file:
            self._create_default_network()
        
        # Initialize SUMO
        if SUMO_AVAILABLE:
            self._initialize_sumo()
        else:
            logger.warning("SUMO not available, using fallback simulation")
            self._initialize_fallback()
    
    def _create_default_network(self):
        """Create a default 4-way intersection network"""
        self.temp_dir = tempfile.mkdtemp()
        self.network_file = os.path.join(self.temp_dir, "intersection.net.xml")
        self.route_file = os.path.join(self.temp_dir, "routes.rou.xml")
        self.config_file = os.path.join(self.temp_dir, "simulation.sumocfg")
        
        # Create network XML
        network_xml = """<?xml version="1.0" encoding="UTF-8"?>
<net version="1.9" junctionCornerDetail="5" lefthand="false" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/net_file.xsd">

    <location netOffset="0.00,0.00" convBoundary="-200.00,-200.00,200.00,200.00" origBoundary="-10000000000.00,-10000000000.00,10000000000.00,10000000000.00" projParameter="!"/>

    <edge id="E0" from="J0" to="J1" priority="1">
        <lane id="E0_0" index="0" speed="13.89" length="200.00" shape="-200.00,-1.60 -100.00,-1.60"/>
        <lane id="E0_1" index="1" speed="13.89" length="200.00" shape="-200.00,1.60 -100.00,1.60"/>
    </edge>
    <edge id="E1" from="J1" to="J2" priority="1">
        <lane id="E1_0" index="0" speed="13.89" length="200.00" shape="100.00,-1.60 200.00,-1.60"/>
        <lane id="E1_1" index="1" speed="13.89" length="200.00" shape="100.00,1.60 200.00,1.60"/>
    </edge>
    <edge id="E2" from="J3" to="J1" priority="1">
        <lane id="E2_0" index="0" speed="13.89" length="200.00" shape="-1.60,-200.00 -1.60,-100.00"/>
        <lane id="E2_1" index="1" speed="13.89" length="200.00" shape="1.60,-200.00 1.60,-100.00"/>
    </edge>
    <edge id="E3" from="J1" to="J4" priority="1">
        <lane id="E3_0" index="0" speed="13.89" length="200.00" shape="-1.60,100.00 -1.60,200.00"/>
        <lane id="E3_1" index="1" speed="13.89" length="200.00" shape="1.60,100.00 1.60,200.00"/>
    </edge>

    <junction id="J0" type="dead_end" x="-200.00" y="0.00" incLanes="" intLanes="" shape="-200.00,3.20 -200.00,-3.20"/>
    <junction id="J1" type="traffic_light" x="0.00" y="0.00" incLanes="E0_0 E0_1 E2_0 E2_1" intLanes=":J1_0_0 :J1_1_0 :J1_2_0 :J1_3_0 :J1_4_0 :J1_5_0 :J1_6_0 :J1_7_0" shape="-100.00,3.20 100.00,3.20 100.56,1.78 101.00,1.00 101.78,0.56 102.89,0.33 104.33,0.33 100.00,-3.20 -100.00,-3.20 -104.33,-0.33 -102.89,-0.33 -101.78,-0.56 -101.00,-1.00 -100.56,-1.78">
        <request index="0" response="00000000" foes="11000000" cont="0"/>
        <request index="1" response="00100000" foes="01100000" cont="0"/>
        <request index="2" response="00000000" foes="00000000" cont="0"/>
        <request index="3" response="00000000" foes="00000111" cont="0"/>
        <request index="4" response="00000100" foes="00000110" cont="0"/>
        <request index="5" response="00000000" foes="00000000" cont="0"/>
        <request index="6" response="00000000" foes="00110000" cont="0"/>
        <request index="7" response="00001000" foes="00001100" cont="0"/>
    </junction>
    <junction id="J2" type="dead_end" x="200.00" y="0.00" incLanes="E1_0 E1_1" intLanes="" shape="200.00,-3.20 200.00,3.20"/>
    <junction id="J3" type="dead_end" x="0.00" y="-200.00" incLanes="" intLanes="" shape="3.20,-200.00 -3.20,-200.00"/>
    <junction id="J4" type="dead_end" x="0.00" y="200.00" incLanes="E3_0 E3_1" intLanes="" shape="-3.20,200.00 3.20,200.00"/>

    <tlLogic id="J1" type="static" programID="0" offset="0">
        <phase duration="30" state="GGrrGGrr"/>
        <phase duration="5" state="yyrryyrr"/>
        <phase duration="30" state="rrGGrrGG"/>
        <phase duration="5" state="rryyrryy"/>
    </tlLogic>

    <connection from="E0" to="E1" fromLane="0" toLane="0" via=":J1_0_0" tl="J1" linkIndex="0" dir="s" state="G"/>
    <connection from="E0" to="E3" fromLane="1" toLane="1" via=":J1_1_0" tl="J1" linkIndex="1" dir="l" state="G"/>
    <connection from="E2" to="E3" fromLane="0" toLane="0" via=":J1_2_0" tl="J1" linkIndex="2" dir="s" state="r"/>
    <connection from="E2" to="E1" fromLane="1" toLane="1" via=":J1_3_0" tl="J1" linkIndex="3" dir="l" state="r"/>

</net>"""
        
        with open(self.network_file, 'w') as f:
            f.write(network_xml)
        
        # Create routes XML
        routes_xml = """<?xml version="1.0" encoding="UTF-8"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
    
    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5.0" maxSpeed="50.0"/>
    <vType id="truck" accel="1.8" decel="4.0" sigma="0.5" length="12.0" maxSpeed="40.0"/>
    <vType id="bus" accel="1.5" decel="4.0" sigma="0.5" length="15.0" maxSpeed="35.0"/>
    <vType id="emergency" accel="3.0" decel="5.0" sigma="0.2" length="6.0" maxSpeed="60.0" color="1,0,0"/>
    
    <route id="route_EW" edges="E0 E1"/>
    <route id="route_WE" edges="E1 E0"/>
    <route id="route_NS" edges="E2 E3"/>
    <route id="route_SN" edges="E3 E2"/>
    
    <flow id="flow_EW" route="route_EW" begin="0" end="3600" vehsPerHour="600" type="car"/>
    <flow id="flow_WE" route="route_WE" begin="0" end="3600" vehsPerHour="600" type="car"/>
    <flow id="flow_NS" route="route_NS" begin="0" end="3600" vehsPerHour="400" type="car"/>
    <flow id="flow_SN" route="route_SN" begin="0" end="3600" vehsPerHour="400" type="car"/>
    
    <flow id="trucks_EW" route="route_EW" begin="0" end="3600" vehsPerHour="100" type="truck"/>
    <flow id="buses_NS" route="route_NS" begin="0" end="3600" vehsPerHour="50" type="bus"/>
    
</routes>"""
        
        with open(self.route_file, 'w') as f:
            f.write(routes_xml)
        
        # Create config XML
        config_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="{os.path.basename(self.network_file)}"/>
        <route-files value="{os.path.basename(self.route_file)}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="{self.simulation_time}"/>
        <step-length value="{self.step_length}"/>
    </time>
    <processing>
        <collision.action value="warn"/>
    </processing>
    <output>
        <tripinfo-output value="tripinfo.xml"/>
        <summary-output value="summary.xml"/>
    </output>
</configuration>"""
        
        with open(self.config_file, 'w') as f:
            f.write(config_xml)
    
    def _initialize_sumo(self):
        """Initialize SUMO simulation"""
        if not SUMO_AVAILABLE:
            return
        
        # SUMO command
        sumo_binary = "sumo-gui" if self.gui else "sumo"
        sumo_cmd = [
            sumo_binary,
            "-c", self.config_file,
            "--step-length", str(self.step_length),
            "--no-warnings", "true",
            "--duration-log.statistics", "true"
        ]
        
        try:
            # Start SUMO
            traci.start(sumo_cmd, label=self.connection_label)
            self.is_running = True
            
            # Get traffic light IDs
            self.traffic_lights = {tl_id: {} for tl_id in traci.trafficlight.getIDList()}
            
            logger.info(f"SUMO simulation initialized with {len(self.traffic_lights)} traffic lights")
            
        except Exception as e:
            logger.error(f"Failed to start SUMO: {e}")
            self._initialize_fallback()
    
    def _initialize_fallback(self):
        """Initialize fallback simulation when SUMO is not available"""
        self.is_running = True
        
        # Simulate basic intersection
        self.traffic_lights = {
            'J1': {
                'phases': ['GGrrGGrr', 'yyrryyrr', 'rrGGrrGG', 'rryyrryy'],
                'current_phase': 0,
                'phase_duration': [30, 5, 30, 5],
                'time_in_phase': 0
            }
        }
        
        # Fallback intersection data
        self.intersection_data = {
            'lanes': ['E0_0', 'E0_1', 'E1_0', 'E1_1', 'E2_0', 'E2_1', 'E3_0', 'E3_1'],
            'detectors': {lane: {'vehicles': np.random.randint(0, 10)} for lane in ['E0_0', 'E0_1', 'E1_0', 'E1_1', 'E2_0', 'E2_1', 'E3_0', 'E3_1']}
        }
        
        logger.info("Fallback simulation initialized")
    
    def step(self) -> Dict[str, Any]:
        """Execute one simulation step"""
        if not self.is_running:
            return {}
        
        if SUMO_AVAILABLE and self.connection_label in traci.getLoadedIDList():
            return self._sumo_step()
        else:
            return self._fallback_step()
    
    def _sumo_step(self) -> Dict[str, Any]:
        """Execute one SUMO simulation step"""
        try:
            # Execute simulation step
            traci.simulationStep()
            self.current_time = traci.simulation.getTime()
            
            # Collect traffic data
            traffic_data = self._collect_sumo_data()
            
            # Update metrics
            self._update_metrics_sumo()
            
            # Check if simulation is finished
            if traci.simulation.getMinExpectedNumber() <= 0:
                self.is_running = False
            
            return traffic_data
            
        except Exception as e:
            logger.error(f"SUMO step failed: {e}")
            self.is_running = False
            return {}
    
    def _fallback_step(self) -> Dict[str, Any]:
        """Execute one fallback simulation step"""
        self.current_time += self.step_length
        
        # Update traffic light phases
        for tl_id, tl_data in self.traffic_lights.items():
            tl_data['time_in_phase'] += self.step_length
            
            current_phase_duration = tl_data['phase_duration'][tl_data['current_phase']]
            if tl_data['time_in_phase'] >= current_phase_duration:
                tl_data['current_phase'] = (tl_data['current_phase'] + 1) % len(tl_data['phases'])
                tl_data['time_in_phase'] = 0
        
        # Simulate vehicle movements
        for lane, detector in self.intersection_data['detectors'].items():
            # Random vehicle arrival/departure
            detector['vehicles'] += np.random.poisson(0.3)  # Arrivals
            detector['vehicles'] = max(0, detector['vehicles'] - np.random.poisson(0.4))  # Departures
            detector['vehicles'] = min(detector['vehicles'], 50)  # Max capacity
        
        # Collect traffic data
        traffic_data = self._collect_fallback_data()
        
        # Check if simulation is finished
        if self.current_time >= self.simulation_time:
            self.is_running = False
        
        return traffic_data
    
    def _collect_sumo_data(self) -> Dict[str, Any]:
        """Collect traffic data from SUMO"""
        data = {
            'timestamp': self.current_time,
            'traffic_lights': {},
            'detectors': {},
            'vehicles': {},
            'performance': {}
        }
        
        # Traffic light data
        for tl_id in self.traffic_lights:
            try:
                data['traffic_lights'][tl_id] = {
                    'current_phase': traci.trafficlight.getPhase(tl_id),
                    'next_switch': traci.trafficlight.getNextSwitch(tl_id),
                    'phase_duration': traci.trafficlight.getPhaseDuration(tl_id),
                    'controlled_lanes': traci.trafficlight.getControlledLanes(tl_id)
                }
            except:
                pass
        
        # Detector data (lane-based)
        try:
            for lane_id in traci.lane.getIDList():
                if not lane_id.startswith(':'):  # Exclude internal lanes
                    data['detectors'][lane_id] = {
                        'vehicle_count': traci.lane.getLastStepVehicleNumber(lane_id),
                        'occupancy': traci.lane.getLastStepOccupancy(lane_id),
                        'mean_speed': traci.lane.getLastStepMeanSpeed(lane_id),
                        'waiting_time': traci.lane.getWaitingTime(lane_id),
                        'queue_length': traci.lane.getLastStepHaltingNumber(lane_id)
                    }
        except:
            pass
        
        # Vehicle data
        try:
            vehicle_ids = traci.vehicle.getIDList()
            data['vehicles'] = {
                'total_count': len(vehicle_ids),
                'average_speed': np.mean([traci.vehicle.getSpeed(vid) for vid in vehicle_ids]) if vehicle_ids else 0,
                'emergency_vehicles': [vid for vid in vehicle_ids if traci.vehicle.getTypeID(vid) == 'emergency']
            }
        except:
            data['vehicles'] = {'total_count': 0, 'average_speed': 0, 'emergency_vehicles': []}
        
        return data
    
    def _collect_fallback_data(self) -> Dict[str, Any]:
        """Collect traffic data from fallback simulation"""
        data = {
            'timestamp': self.current_time,
            'traffic_lights': {},
            'detectors': {},
            'vehicles': {},
            'performance': {}
        }
        
        # Traffic light data
        for tl_id, tl_data in self.traffic_lights.items():
            data['traffic_lights'][tl_id] = {
                'current_phase': tl_data['current_phase'],
                'phase_state': tl_data['phases'][tl_data['current_phase']],
                'time_in_phase': tl_data['time_in_phase'],
                'phase_duration': tl_data['phase_duration'][tl_data['current_phase']]
            }
        
        # Detector data
        for lane_id, detector in self.intersection_data['detectors'].items():
            vehicles = detector['vehicles']
            data['detectors'][lane_id] = {
                'vehicle_count': vehicles,
                'occupancy': min(vehicles / 20.0, 1.0),  # Normalized occupancy
                'mean_speed': np.random.uniform(20, 50) if vehicles > 0 else 0,
                'waiting_time': vehicles * np.random.uniform(5, 15),
                'queue_length': max(0, vehicles - 5)
            }
        
        # Vehicle data
        total_vehicles = sum(d['vehicles'] for d in self.intersection_data['detectors'].values())
        data['vehicles'] = {
            'total_count': total_vehicles,
            'average_speed': np.random.uniform(25, 45),
            'emergency_vehicles': []
        }
        
        return data
    
    def _update_metrics_sumo(self):
        """Update performance metrics from SUMO"""
        if not SUMO_AVAILABLE:
            return
        
        try:
            # Update basic metrics
            self.metrics['total_vehicles'] = len(traci.vehicle.getIDList())
            
            # Get completed trips (if tripinfo is available)
            if hasattr(traci, 'simulation'):
                self.metrics['completed_trips'] = traci.simulation.getArrivedNumber()
            
            # Calculate average speed
            vehicle_ids = traci.vehicle.getIDList()
            if vehicle_ids:
                speeds = [traci.vehicle.getSpeed(vid) for vid in vehicle_ids]
                self.metrics['average_speed'] = np.mean(speeds)
            
            # Calculate total waiting time
            total_waiting = 0
            for lane_id in traci.lane.getIDList():
                if not lane_id.startswith(':'):
                    total_waiting += traci.lane.getWaitingTime(lane_id)
            self.metrics['total_waiting_time'] = total_waiting
            
        except Exception as e:
            logger.warning(f"Failed to update SUMO metrics: {e}")
    
    def set_traffic_light_phase(self, tl_id: str, phase: int, duration: Optional[float] = None):
        """Set traffic light phase"""
        if not self.is_running:
            return
        
        if SUMO_AVAILABLE and self.connection_label in traci.getLoadedIDList():
            try:
                traci.trafficlight.setPhase(tl_id, phase)
                if duration:
                    traci.trafficlight.setPhaseDuration(tl_id, duration)
            except Exception as e:
                logger.error(f"Failed to set traffic light phase: {e}")
        else:
            # Fallback mode
            if tl_id in self.traffic_lights:
                self.traffic_lights[tl_id]['current_phase'] = phase
                self.traffic_lights[tl_id]['time_in_phase'] = 0
                if duration:
                    self.traffic_lights[tl_id]['phase_duration'][phase] = duration
    
    def add_emergency_vehicle(self, route: str, depart_time: float = 0):
        """Add emergency vehicle to simulation"""
        if not self.is_running:
            return
        
        vehicle_id = f"emergency_{int(time.time())}"
        
        if SUMO_AVAILABLE and self.connection_label in traci.getLoadedIDList():
            try:
                traci.vehicle.add(
                    vehID=vehicle_id,
                    routeID=route,
                    typeID="emergency",
                    depart=str(depart_time)
                )
                logger.info(f"Emergency vehicle {vehicle_id} added")
            except Exception as e:
                logger.error(f"Failed to add emergency vehicle: {e}")
    
    def get_intersection_state(self) -> Dict[str, Any]:
        """Get current intersection state for DRL agent"""
        traffic_data = self.step()
        
        if not traffic_data:
            return {}
        
        # Extract state information for DRL
        state = {
            'lane_densities': [],
            'queue_lengths': [],
            'waiting_times': [],
            'current_phase': 0,
            'phase_elapsed': 0,
            'emergency_vehicles': len(traffic_data.get('vehicles', {}).get('emergency_vehicles', [])),
            'timestamp': self.current_time
        }
        
        # Process detector data
        detectors = traffic_data.get('detectors', {})
        for lane_id in sorted(detectors.keys()):
            detector = detectors[lane_id]
            state['lane_densities'].append(detector.get('occupancy', 0))
            state['queue_lengths'].append(detector.get('queue_length', 0))
            state['waiting_times'].append(detector.get('waiting_time', 0))
        
        # Process traffic light data
        tl_data = traffic_data.get('traffic_lights', {})
        if tl_data:
            first_tl = list(tl_data.values())[0]
            state['current_phase'] = first_tl.get('current_phase', 0)
            state['phase_elapsed'] = first_tl.get('time_in_phase', 0)
        
        return state
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get simulation performance metrics"""
        if SUMO_AVAILABLE and self.connection_label in traci.getLoadedIDList():
            self._update_metrics_sumo()
        
        return self.metrics.copy()
    
    def close(self):
        """Close simulation"""
        if SUMO_AVAILABLE and self.connection_label in traci.getLoadedIDList():
            try:
                traci.close(label=self.connection_label)
            except:
                pass
        
        self.is_running = False
        
        # Clean up temporary files
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        logger.info("SUMO simulation closed")
    
    def __del__(self):
        """Destructor"""
        self.close()


class SUMOEnvironmentWrapper:
    """
    Wrapper to integrate SUMO simulation with DRL environment
    """
    
    def __init__(
        self,
        sumo_config: Dict[str, Any] = None,
        observation_space_size: int = 32,
        action_space_size: int = 2
    ):
        """
        Initialize SUMO environment wrapper
        
        Args:
            sumo_config: SUMO configuration parameters
            observation_space_size: Size of observation space
            action_space_size: Size of action space
        """
        self.sumo_config = sumo_config or {}
        self.observation_space_size = observation_space_size
        self.action_space_size = action_space_size
        
        # Initialize SUMO simulation
        self.simulation = SUMOTrafficSimulation(**self.sumo_config)
        
        # State normalization parameters
        self.state_normalizers = {
            'density_max': 1.0,
            'queue_max': 50.0,
            'waiting_max': 300.0,
            'phase_max': 4.0
        }
    
    def reset(self) -> np.ndarray:
        """Reset environment"""
        # Close existing simulation
        self.simulation.close()
        
        # Start new simulation
        self.simulation = SUMOTrafficSimulation(**self.sumo_config)
        
        # Get initial state
        return self._get_normalized_state()
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        """Execute one environment step"""
        # Decode action
        phase_selection = int(action[0] * 4)  # 4 phases
        duration = 5 + action[1] * 55  # 5-60 seconds
        
        # Apply action to traffic light
        tl_ids = list(self.simulation.traffic_lights.keys())
        if tl_ids:
            self.simulation.set_traffic_light_phase(tl_ids[0], phase_selection, duration)
        
        # Get new state
        state = self._get_normalized_state()
        
        # Calculate reward
        reward = self._calculate_reward()
        
        # Check if done
        done = not self.simulation.is_running
        
        # Get info
        info = {
            'metrics': self.simulation.get_performance_metrics(),
            'current_time': self.simulation.current_time
        }
        
        return state, reward, done, info
    
    def _get_normalized_state(self) -> np.ndarray:
        """Get normalized state vector"""
        intersection_state = self.simulation.get_intersection_state()
        
        if not intersection_state:
            return np.zeros(self.observation_space_size)
        
        # Normalize state components
        densities = np.array(intersection_state.get('lane_densities', [0] * 8))
        queues = np.array(intersection_state.get('queue_lengths', [0] * 8))
        waiting = np.array(intersection_state.get('waiting_times', [0] * 8))
        
        # Normalize
        norm_densities = np.clip(densities / self.state_normalizers['density_max'], 0, 1)
        norm_queues = np.clip(queues / self.state_normalizers['queue_max'], 0, 1)
        norm_waiting = np.clip(waiting / self.state_normalizers['waiting_max'], 0, 1)
        
        # Phase information
        phase_info = np.zeros(4)
        current_phase = intersection_state.get('current_phase', 0)
        if current_phase < 4:
            phase_info[current_phase] = 1.0
        
        # Combine state
        state = np.concatenate([
            norm_densities,
            norm_queues,
            norm_waiting,
            phase_info,
            [intersection_state.get('phase_elapsed', 0) / 60.0],  # Normalized elapsed time
            [intersection_state.get('emergency_vehicles', 0) > 0],  # Emergency flag
            [self.simulation.current_time / 3600.0],  # Normalized time
            [0.0]  # Padding
        ])
        
        # Ensure correct size
        if len(state) > self.observation_space_size:
            state = state[:self.observation_space_size]
        elif len(state) < self.observation_space_size:
            state = np.pad(state, (0, self.observation_space_size - len(state)))
        
        return state.astype(np.float32)
    
    def _calculate_reward(self) -> float:
        """Calculate reward based on traffic performance"""
        metrics = self.simulation.get_performance_metrics()
        
        # Multi-objective reward
        throughput_reward = metrics.get('completed_trips', 0) * 0.1
        waiting_penalty = -metrics.get('total_waiting_time', 0) * 0.001
        speed_reward = metrics.get('average_speed', 0) * 0.01
        
        total_reward = throughput_reward + waiting_penalty + speed_reward
        
        return total_reward
    
    def close(self):
        """Close environment"""
        self.simulation.close()


def main():
    """Test SUMO simulation environment"""
    print("Testing SUMO Traffic Simulation...")
    
    # Test basic simulation
    sim = SUMOTrafficSimulation(gui=False, simulation_time=300)
    
    print(f"Simulation running: {sim.is_running}")
    print(f"Traffic lights: {list(sim.traffic_lights.keys())}")
    
    # Run simulation for a few steps
    for step in range(50):
        traffic_data = sim.step()
        
        if step % 10 == 0:
            state = sim.get_intersection_state()
            metrics = sim.get_performance_metrics()
            print(f"Step {step}: Time={sim.current_time:.1f}s, "
                  f"Vehicles={metrics.get('total_vehicles', 0)}, "
                  f"Avg Speed={metrics.get('average_speed', 0):.1f}")
        
        if not sim.is_running:
            break
    
    # Test traffic light control
    print("\nTesting traffic light control...")
    if sim.traffic_lights:
        tl_id = list(sim.traffic_lights.keys())[0]
        sim.set_traffic_light_phase(tl_id, 2, 45)  # Set phase 2 for 45 seconds
        print(f"Set traffic light {tl_id} to phase 2")
    
    # Test emergency vehicle
    print("\nTesting emergency vehicle...")
    sim.add_emergency_vehicle("route_EW", 0)
    
    # Continue simulation
    for step in range(20):
        traffic_data = sim.step()
        if not sim.is_running:
            break
    
    # Final metrics
    final_metrics = sim.get_performance_metrics()
    print(f"\nFinal metrics: {final_metrics}")
    
    # Close simulation
    sim.close()
    print("Simulation closed.")


if __name__ == "__main__":
    main()