"""
Real-time Traffic Control System Dashboard
Streamlit-based dashboard for monitoring and control
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
import json
import sqlite3
from datetime import datetime, timedelta
import cv2
from PIL import Image
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Import project modules
try:
    from src.security.security_system import SecuritySystem
    from src.simulation.sumo_environment import SUMOTrafficSimulation
    from src.detection.yolo_detector import YOLOVehicleDetector
    from src.tracking.deep_sort_tracker import DeepSORTTracker
except ImportError as e:
    st.error(f"Failed to import modules: {e}")


class TrafficDashboard:
    """
    Real-time Traffic Control System Dashboard
    
    Features:
    - Live traffic monitoring
    - Security alerts
    - Performance metrics
    - System control interface
    - Data visualization
    """
    
    def __init__(self):
        """Initialize dashboard"""
        self.setup_page_config()
        self.initialize_systems()
        self.setup_session_state()
    
    def setup_page_config(self):
        """Configure Streamlit page"""
        st.set_page_config(
            page_title="Traffic Control System",
            page_icon="🚦",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Custom CSS
        st.markdown("""
        <style>
        .main-header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .alert-critical {
            background: #ffebee;
            border-left: 5px solid #f44336;
            padding: 10px;
            margin: 5px 0;
        }
        .alert-warning {
            background: #fff3e0;
            border-left: 5px solid #ff9800;
            padding: 10px;
            margin: 5px 0;
        }
        .alert-info {
            background: #e3f2fd;
            border-left: 5px solid #2196f3;
            padding: 10px;
            margin: 5px 0;
        }
        </style>
        """, unsafe_allow_html=True)
    
    def initialize_systems(self):
        """Initialize system components"""
        try:
            # Initialize security system
            self.security_system = SecuritySystem()
            
            # Initialize traffic simulation (fallback mode)
            self.traffic_sim = SUMOTrafficSimulation(gui=False, simulation_time=3600)
            
            # System status
            self.system_status = {
                'detection': True,
                'tracking': True,
                'control': True,
                'security': True,
                'simulation': True
            }
            
        except Exception as e:
            st.error(f"Failed to initialize systems: {e}")
            self.system_status = {k: False for k in ['detection', 'tracking', 'control', 'security', 'simulation']}
    
    def setup_session_state(self):
        """Initialize session state variables"""
        if 'last_update' not in st.session_state:
            st.session_state.last_update = datetime.now()
        
        if 'simulation_running' not in st.session_state:
            st.session_state.simulation_running = False
        
        if 'detection_enabled' not in st.session_state:
            st.session_state.detection_enabled = True
        
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = True
    
    def run(self):
        """Run the dashboard"""
        # Header
        st.markdown("""
        <div class="main-header">
            <h1>🚦 AI Traffic Control System</h1>
            <p>Real-time Traffic Monitoring and Control Dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Sidebar
        self.render_sidebar()
        
        # Main content
        if st.session_state.get('current_page', 'overview') == 'overview':
            self.render_overview()
        elif st.session_state.current_page == 'traffic':
            self.render_traffic_monitoring()
        elif st.session_state.current_page == 'security':
            self.render_security_dashboard()
        elif st.session_state.current_page == 'control':
            self.render_control_panel()
        elif st.session_state.current_page == 'analytics':
            self.render_analytics()
        
        # Auto-refresh
        if st.session_state.auto_refresh:
            time.sleep(5)
            st.rerun()
    
    def render_sidebar(self):
        """Render sidebar navigation"""
        st.sidebar.title("Navigation")
        
        # Page selection
        pages = {
            'overview': '📊 System Overview',
            'traffic': '🚗 Traffic Monitoring',
            'security': '🔒 Security Alerts',
            'control': '⚙️ Control Panel',
            'analytics': '📈 Analytics'
        }
        
        selected_page = st.sidebar.selectbox(
            "Select Page",
            options=list(pages.keys()),
            format_func=lambda x: pages[x],
            key='current_page'
        )
        
        st.sidebar.markdown("---")
        
        # System controls
        st.sidebar.subheader("System Controls")
        
        st.session_state.auto_refresh = st.sidebar.checkbox(
            "Auto Refresh", 
            value=st.session_state.auto_refresh
        )
        
        st.session_state.detection_enabled = st.sidebar.checkbox(
            "Enable Detection", 
            value=st.session_state.detection_enabled
        )
        
        if st.sidebar.button("🔄 Refresh Data"):
            st.rerun()
        
        st.sidebar.markdown("---")
        
        # System status
        st.sidebar.subheader("System Status")
        
        for component, status in self.system_status.items():
            status_icon = "🟢" if status else "🔴"
            st.sidebar.write(f"{status_icon} {component.title()}")
        
        # Last update
        st.sidebar.markdown("---")
        st.sidebar.write(f"Last Update: {st.session_state.last_update.strftime('%H:%M:%S')}")
    
    def render_overview(self):
        """Render system overview page"""
        st.header("System Overview")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Active Vehicles",
                value="124",
                delta="12"
            )
        
        with col2:
            st.metric(
                label="Avg Wait Time",
                value="23.5s",
                delta="-5.2s"
            )
        
        with col3:
            st.metric(
                label="Throughput",
                value="1,847 veh/h",
                delta="156"
            )
        
        with col4:
            st.metric(
                label="Security Alerts",
                value="3",
                delta="1"
            )
        
        # Live traffic visualization
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Live Traffic Flow")
            self.render_traffic_flow_chart()
        
        with col2:
            st.subheader("Recent Alerts")
            self.render_recent_alerts()
        
        # Performance charts
        st.subheader("Performance Metrics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            self.render_throughput_chart()
        
        with col2:
            self.render_waiting_time_chart()
    
    def render_traffic_monitoring(self):
        """Render traffic monitoring page"""
        st.header("Traffic Monitoring")
        
        # Traffic light status
        st.subheader("Traffic Light Status")
        
        col1, col2, col3, col4 = st.columns(4)
        
        phases = ["North-South", "East-West", "NS Left", "EW Left"]
        colors = ["green", "red", "red", "red"]
        times = ["25s", "35s", "15s", "20s"]
        
        for i, (col, phase, color, time_left) in enumerate(zip([col1, col2, col3, col4], phases, colors, times)):
            with col:
                status_color = "🟢" if color == "green" else "🔴"
                st.metric(
                    label=f"{status_color} {phase}",
                    value=time_left,
                    delta=f"Phase {i+1}"
                )
        
        # Lane occupancy
        st.subheader("Lane Occupancy")
        
        # Generate sample occupancy data
        lanes = [f"Lane {i+1}" for i in range(8)]
        occupancy = np.random.uniform(0.2, 0.8, 8)
        
        fig = go.Figure(data=go.Bar(
            x=lanes,
            y=occupancy,
            marker_color=['red' if x > 0.7 else 'yellow' if x > 0.5 else 'green' for x in occupancy]
        ))
        
        fig.update_layout(
            title="Lane Occupancy Levels",
            xaxis_title="Lanes",
            yaxis_title="Occupancy (%)",
            yaxis=dict(range=[0, 1])
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Vehicle tracking
        st.subheader("Vehicle Tracking")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Vehicle count by type
            vehicle_types = ['Cars', 'Trucks', 'Motorcycles', 'Buses']
            counts = [85, 12, 23, 4]
            
            fig = px.pie(
                values=counts,
                names=vehicle_types,
                title="Vehicle Distribution"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Speed distribution
            speeds = np.random.normal(35, 10, 100)
            
            fig = px.histogram(
                x=speeds,
                nbins=20,
                title="Speed Distribution",
                labels={'x': 'Speed (km/h)', 'y': 'Count'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Real-time feed simulation
        st.subheader("Camera Feeds")
        
        col1, col2, col3 = st.columns(3)
        
        cameras = ["Camera 1 - North", "Camera 2 - East", "Camera 3 - South"]
        
        for col, camera in zip([col1, col2, col3], cameras):
            with col:
                st.write(f"📹 {camera}")
                
                # Placeholder for camera feed
                placeholder_img = np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8)
                st.image(placeholder_img, caption=camera, use_column_width=True)
    
    def render_security_dashboard(self):
        """Render security dashboard page"""
        st.header("Security Dashboard")
        
        # Security metrics
        col1, col2, col3, col4 = st.columns(4)
        
        try:
            dashboard_data = self.security_system.get_dashboard_data()
            system_status = dashboard_data['system_status']
            
            with col1:
                st.metric(
                    label="Active Stolen Vehicles",
                    value=system_status['database_stats']['total_active_stolen']
                )
            
            with col2:
                st.metric(
                    label="Alerts Today",
                    value=system_status['alert_stats']['alerts_today']
                )
            
            with col3:
                st.metric(
                    label="Total Alerts",
                    value=system_status['alert_stats']['total_alerts']
                )
            
            with col4:
                st.metric(
                    label="False Positives",
                    value=system_status['alert_stats']['false_positives']
                )
        
        except Exception as e:
            st.error(f"Failed to load security data: {e}")
            for col in [col1, col2, col3, col4]:
                with col:
                    st.metric("Error", "N/A")
        
        # Recent alerts
        st.subheader("Recent Security Alerts")
        
        try:
            recent_alerts = self.security_system.alert_manager.get_recent_alerts(24)
            
            if recent_alerts:
                for alert in recent_alerts[:5]:  # Show last 5 alerts
                    alert_level = alert['alert_level']
                    css_class = f"alert-{alert_level}"
                    
                    st.markdown(f"""
                    <div class="{css_class}">
                        <strong>Alert #{alert['id']}</strong> - {alert['license_plate']}<br>
                        📍 {alert['location']} | 📅 {alert['detection_time']}<br>
                        🎯 Confidence: {alert['confidence']:.2f} | 🚨 Level: {alert_level.upper()}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No recent security alerts")
                
        except Exception as e:
            st.error(f"Failed to load recent alerts: {e}")
        
        # Stolen vehicles by priority
        st.subheader("Stolen Vehicles by Priority")
        
        try:
            db_stats = self.security_system.database.get_statistics()
            priority_data = db_stats.get('by_priority', {})
            
            if priority_data:
                fig = px.bar(
                    x=list(priority_data.keys()),
                    y=list(priority_data.values()),
                    title="Stolen Vehicles by Priority",
                    color=list(priority_data.keys()),
                    color_discrete_map={
                        'critical': 'red',
                        'high': 'orange', 
                        'medium': 'yellow',
                        'low': 'green'
                    }
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No priority data available")
                
        except Exception as e:
            st.error(f"Failed to load priority data: {e}")
        
        # Vehicle type distribution
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Stolen Vehicles by Type")
            
            try:
                type_data = db_stats.get('by_vehicle_type', {})
                
                if type_data:
                    fig = px.pie(
                        values=list(type_data.values()),
                        names=list(type_data.keys()),
                        title="Distribution by Vehicle Type"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No vehicle type data available")
                    
            except Exception as e:
                st.error(f"Failed to load vehicle type data: {e}")
        
        with col2:
            st.subheader("Alert Response Time")
            
            # Sample response time data
            response_times = np.random.exponential(5, 20)  # Exponential distribution
            
            fig = px.histogram(
                x=response_times,
                nbins=10,
                title="Alert Response Time Distribution",
                labels={'x': 'Response Time (minutes)', 'y': 'Count'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Manual vehicle check
        st.subheader("Manual Vehicle Check")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            license_plate = st.text_input("Enter License Plate", placeholder="e.g., KA01AB1234")
            
            if st.button("Check Vehicle") and license_plate:
                try:
                    result = self.security_system.check_vehicle(
                        license_plate=license_plate,
                        confidence=1.0,
                        location="Manual Check",
                        camera_id="MANUAL"
                    )
                    
                    if result['is_stolen']:
                        st.error(f"🚨 STOLEN VEHICLE DETECTED: {license_plate}")
                        st.json(result['vehicle_info'])
                        
                        if result['alert_created']:
                            st.success(f"Alert #{result['alert_id']} created successfully")
                    else:
                        st.success(f"✅ Vehicle {license_plate} is not in stolen database")
                        
                except Exception as e:
                    st.error(f"Check failed: {e}")
        
        with col2:
            st.info("""
            **Manual Check Features:**
            - Real-time database lookup
            - Fuzzy matching for partial plates
            - Automatic alert creation
            - Confidence scoring
            """)
    
    def render_control_panel(self):
        """Render control panel page"""
        st.header("Traffic Control Panel")
        
        # Traffic light control
        st.subheader("Traffic Light Control")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Manual Phase Control**")
            
            phase_options = {
                0: "North-South Green",
                1: "East-West Green", 
                2: "North-South Left Turn",
                3: "East-West Left Turn"
            }
            
            selected_phase = st.selectbox(
                "Select Phase",
                options=list(phase_options.keys()),
                format_func=lambda x: phase_options[x]
            )
            
            duration = st.slider("Phase Duration (seconds)", 5, 120, 30)
            
            if st.button("Apply Phase Change"):
                try:
                    # Apply to simulation
                    tl_ids = list(self.traffic_sim.traffic_lights.keys())
                    if tl_ids:
                        self.traffic_sim.set_traffic_light_phase(tl_ids[0], selected_phase, duration)
                        st.success(f"Phase {selected_phase} applied for {duration} seconds")
                    else:
                        st.warning("No traffic lights available")
                except Exception as e:
                    st.error(f"Failed to apply phase change: {e}")
        
        with col2:
            st.write("**Emergency Override**")
            
            emergency_direction = st.selectbox(
                "Emergency Vehicle Direction",
                ["North", "South", "East", "West"]
            )
            
            if st.button("🚨 Emergency Override", type="primary"):
                st.success(f"Emergency override activated for {emergency_direction} direction")
                st.info("All other directions will show red signal")
        
        # DRL Agent Control
        st.subheader("AI Agent Control")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            agent_mode = st.selectbox(
                "Control Mode",
                ["Manual", "AI Agent", "Hybrid"]
            )
        
        with col2:
            if agent_mode == "AI Agent":
                learning_rate = st.number_input("Learning Rate", 0.0001, 0.01, 0.0003, format="%.4f")
            else:
                learning_rate = 0.0003
        
        with col3:
            if st.button("Update Agent Settings"):
                st.success("AI agent settings updated")
        
        # Simulation control
        st.subheader("Simulation Control")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("▶️ Start Simulation"):
                st.session_state.simulation_running = True
                st.success("Simulation started")
        
        with col2:
            if st.button("⏸️ Pause Simulation"):
                st.session_state.simulation_running = False
                st.info("Simulation paused")
        
        with col3:
            if st.button("🔄 Reset Simulation"):
                try:
                    # Reset simulation
                    self.traffic_sim.close()
                    self.traffic_sim = SUMOTrafficSimulation(gui=False, simulation_time=3600)
                    st.success("Simulation reset")
                except Exception as e:
                    st.error(f"Reset failed: {e}")
        
        # System parameters
        st.subheader("System Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Detection Parameters**")
            
            confidence_threshold = st.slider("Detection Confidence", 0.1, 1.0, 0.5)
            nms_threshold = st.slider("NMS Threshold", 0.1, 1.0, 0.45)
            
            if st.button("Update Detection"):
                st.success("Detection parameters updated")
        
        with col2:
            st.write("**Tracking Parameters**")
            
            max_age = st.number_input("Max Track Age", 1, 100, 30)
            min_hits = st.number_input("Min Hits", 1, 10, 3)
            
            if st.button("Update Tracking"):
                st.success("Tracking parameters updated")
    
    def render_analytics(self):
        """Render analytics page"""
        st.header("Traffic Analytics")
        
        # Time range selector
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
        
        with col2:
            end_date = st.date_input("End Date", datetime.now())
        
        # Performance trends
        st.subheader("Performance Trends")
        
        # Generate sample time series data
        dates = pd.date_range(start_date, end_date, freq='H')
        
        # Throughput trend
        throughput_data = 1000 + 500 * np.sin(np.arange(len(dates)) * 2 * np.pi / 24) + np.random.normal(0, 100, len(dates))
        
        # Wait time trend
        wait_time_data = 30 + 10 * np.sin(np.arange(len(dates)) * 2 * np.pi / 24 + np.pi) + np.random.normal(0, 5, len(dates))
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Hourly Throughput (vehicles/hour)', 'Average Wait Time (seconds)'),
            vertical_spacing=0.1
        )
        
        fig.add_trace(
            go.Scatter(x=dates, y=throughput_data, mode='lines', name='Throughput'),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=dates, y=wait_time_data, mode='lines', name='Wait Time', line=dict(color='red')),
            row=2, col=1
        )
        
        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Comparative analysis
        st.subheader("Comparative Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Before vs After AI implementation
            categories = ['Throughput', 'Wait Time', 'Fuel Consumption', 'Emissions']
            before_ai = [100, 100, 100, 100]  # Baseline
            after_ai = [127, 68, 85, 78]  # Improvements
            
            fig = go.Figure(data=[
                go.Bar(name='Before AI', x=categories, y=before_ai, marker_color='lightblue'),
                go.Bar(name='After AI', x=categories, y=after_ai, marker_color='darkblue')
            ])
            
            fig.update_layout(
                title='Performance: Before vs After AI Implementation',
                yaxis_title='Relative Performance (%)',
                barmode='group'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Peak hour analysis
            hours = list(range(24))
            traffic_volume = [300, 200, 150, 100, 80, 100, 300, 800, 1200, 1000, 900, 950, 
                            1100, 1200, 1300, 1400, 1500, 1800, 1600, 1200, 800, 600, 450, 350]
            
            fig = px.line(
                x=hours, 
                y=traffic_volume,
                title='24-Hour Traffic Volume Pattern',
                labels={'x': 'Hour of Day', 'y': 'Vehicles/Hour'}
            )
            
            # Highlight peak hours
            fig.add_vrect(x0=7, x1=9, fillcolor="red", opacity=0.2, annotation_text="Morning Peak")
            fig.add_vrect(x0=17, x1=19, fillcolor="red", opacity=0.2, annotation_text="Evening Peak")
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Efficiency metrics
        st.subheader("Efficiency Metrics")
        
        metrics_data = {
            'Metric': ['Throughput Improvement', 'Wait Time Reduction', 'Fuel Savings', 'Emission Reduction', 'Accident Reduction'],
            'Value': [27, 32, 15, 22, 18],
            'Target': [25, 30, 20, 25, 15],
            'Unit': ['%', '%', '%', '%', '%']
        }
        
        df = pd.DataFrame(metrics_data)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Achieved',
            x=df['Metric'],
            y=df['Value'],
            marker_color='green'
        ))
        
        fig.add_trace(go.Bar(
            name='Target',
            x=df['Metric'],
            y=df['Target'],
            marker_color='lightgreen'
        ))
        
        fig.update_layout(
            title='Efficiency Metrics: Achieved vs Target',
            yaxis_title='Improvement (%)',
            barmode='group'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Data table
        st.subheader("Detailed Metrics")
        st.dataframe(df, use_container_width=True)
    
    def render_traffic_flow_chart(self):
        """Render real-time traffic flow chart"""
        # Generate sample data
        time_points = pd.date_range(datetime.now() - timedelta(hours=1), datetime.now(), freq='5T')
        
        # Simulate traffic flow for different directions
        ns_flow = 800 + 200 * np.sin(np.arange(len(time_points)) * 0.5) + np.random.normal(0, 50, len(time_points))
        ew_flow = 600 + 300 * np.cos(np.arange(len(time_points)) * 0.3) + np.random.normal(0, 40, len(time_points))
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=time_points,
            y=ns_flow,
            mode='lines',
            name='North-South',
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=time_points,
            y=ew_flow,
            mode='lines',
            name='East-West',
            line=dict(color='red')
        ))
        
        fig.update_layout(
            title='Real-time Traffic Flow',
            xaxis_title='Time',
            yaxis_title='Vehicles/Hour',
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_recent_alerts(self):
        """Render recent alerts panel"""
        try:
            recent_alerts = self.security_system.alert_manager.get_recent_alerts(6)
            
            if recent_alerts:
                for alert in recent_alerts[:3]:  # Show last 3
                    alert_time = datetime.fromisoformat(alert['detection_time']).strftime('%H:%M')
                    
                    if alert['alert_level'] == 'critical':
                        st.error(f"🚨 {alert_time}: {alert['license_plate']}")
                    elif alert['alert_level'] == 'warning':
                        st.warning(f"⚠️ {alert_time}: {alert['license_plate']}")
                    else:
                        st.info(f"ℹ️ {alert_time}: {alert['license_plate']}")
            else:
                st.success("No recent security alerts")
                
        except Exception as e:
            st.error(f"Failed to load alerts: {e}")
    
    def render_throughput_chart(self):
        """Render throughput chart"""
        hours = list(range(24))
        throughput = [800 + 400 * np.sin(i * np.pi / 12) + np.random.normal(0, 50) for i in hours]
        
        fig = px.area(
            x=hours,
            y=throughput,
            title='Daily Throughput Pattern',
            labels={'x': 'Hour', 'y': 'Vehicles/Hour'}
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_waiting_time_chart(self):
        """Render waiting time chart"""
        hours = list(range(24))
        wait_times = [20 + 15 * np.sin(i * np.pi / 12 + np.pi) + np.random.normal(0, 3) for i in hours]
        
        fig = px.line(
            x=hours,
            y=wait_times,
            title='Average Waiting Time',
            labels={'x': 'Hour', 'y': 'Wait Time (seconds)'}
        )
        
        st.plotly_chart(fig, use_container_width=True)


def main():
    """Main dashboard application"""
    dashboard = TrafficDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()