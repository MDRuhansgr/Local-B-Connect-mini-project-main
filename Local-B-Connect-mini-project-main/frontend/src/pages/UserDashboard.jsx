import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";
import { Navbar, Nav, Button, Form, Row, Col, Card, Spinner, Alert, InputGroup } from "react-bootstrap";

const SERVICE_CATEGORIES = [
  "All", "Tutor", "Plumber", "Electrician", "Sweeper", "Salon", "Spa", "Beauty Parlour"
];

function UserDashboard() {
  const [services, setServices] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [category, setCategory] = useState("All");
  const [search, setSearch] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState({ show: false, variant: '', message: '' });
  const [bookings, setBookings] = useState([]);
  const [loadingBookings, setLoadingBookings] = useState(false);
  const navigate = useNavigate();

  
  const handleLogout = () => {
    localStorage.clear();
    window.location.href = "/login";
  };

  

  
  useEffect(() => {
    const fetchBookings = async () => {
      setLoadingBookings(true);
      try {
        const token = localStorage.getItem("token");
        const res = await axios.get("http://localhost:5000/api/bookings/my", {
          headers: { Authorization: `Bearer ${token}` }
        });
        setBookings(res.data);
      } catch {
        setBookings([]);
      } finally {
        setLoadingBookings(false);
      }
    };
    fetchBookings();
  }, []);

  
  useEffect(() => {
    const fetchServices = async () => {
      setLoading(true);
      try {
        const res = await axios.get("http://localhost:5000/api/services/all");
        setServices(res.data);
        setFiltered(res.data);
      } catch {
        setAlert({ show: true, variant: 'danger', message: 'Failed to fetch services.' });
      } finally {
        setLoading(false);
      }
    };
    fetchServices();
  }, []);

  
  useEffect(() => {
    let filteredData = [...services];
    // Category filter
    if (category !== "All") {
      filteredData = filteredData.filter(s => s.type === category);
    }
    // Search filter (by name/type/description)
    if (search) {
      filteredData = filteredData.filter(s =>
        (s.name && s.name.toLowerCase().includes(search.toLowerCase())) ||
        (s.type && s.type.toLowerCase().includes(search.toLowerCase())) ||
        (s.description && s.description.toLowerCase().includes(search.toLowerCase()))
      );
    }
    setFiltered(filteredData);
  }, [services, category, search]);

  return (
    <>
      
      <Navbar bg="primary" variant="dark" expand="lg" className="mb-4">
        <div className="container">
          <Navbar.Brand>Local-B-Connect</Navbar.Brand>
          <Navbar.Toggle aria-controls="user-navbar" />
          <Navbar.Collapse id="user-navbar">
            <Nav className="me-auto">
              <Nav.Item>
                <span className="nav-link">User Dashboard</span>
              </Nav.Item>
            </Nav>
            <Button variant="outline-light" onClick={handleLogout}>Logout</Button>
          </Navbar.Collapse>
        </div>
      </Navbar>
      <div className="container">
        
        <h2 className="mb-4 text-primary">My Booked Services</h2>
        {loadingBookings ? (
          <div className="text-center py-3"><Spinner animation="border" /></div>
        ) : bookings.length === 0 ? (
          <div className="text-muted mb-4">You have not booked any services yet.</div>
        ) : (
          <div className="table-responsive mb-4">
            <table className="table table-bordered align-middle">
              <thead className="table-light">
                <tr>
                  <th>Service</th>
                  <th>Provider</th>
                  <th>Date</th>
                  <th>Time</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {bookings.map((b, i) => (
                  <tr key={b._id || i}>
                    <td>{b.service?.name || '-'}</td>
                    <td>{b.provider?.name || '-'}</td>
                    <td>{b.date ? new Date(b.date).toLocaleDateString() : '-'}</td>
                    <td>{b.time || '-'}</td>
                    <td>
                      {b.status === 'confirmed' ? (
                        <span className="badge bg-success">Booking Success</span>
                      ) : b.status === 'rejected' ? (
                        <span className="badge bg-danger">Rejected</span>
                      ) : (
                        <span className="badge bg-secondary">{b.status || '-'}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <h2 className="mb-4 text-primary">Find Services Near You</h2>
        <Row className="mb-3 g-2 align-items-center">
          <Col md={4} sm={12}>
            <Form.Select value={category} onChange={e => setCategory(e.target.value)}>
              {SERVICE_CATEGORIES.map(cat => <option key={cat} value={cat}>{cat}</option>)}
            </Form.Select>
          </Col>
          <Col md={4} sm={12}>
            <InputGroup>
              <Form.Control
                placeholder="Search services (name, type, description)"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
              <Button variant="outline-secondary" onClick={() => setSearch("")}>Clear</Button>
            </InputGroup>
          </Col>
        </Row>
        {alert.show && (
          <Alert variant={alert.variant} onClose={() => setAlert({ ...alert, show: false })} dismissible>{alert.message}</Alert>
        )}
        {loading ? (
          <div className="text-center py-5"><Spinner animation="border" /></div>
        ) : (
          filtered.length === 0 ? (
            <div className="text-center py-5 text-muted">No services found for your filters/location.</div>
          ) : (
            <Row xs={1} md={2} lg={3} className="g-4">
              {filtered.map(s => (
                <Col key={s._id}>
                  <Card className="h-100 shadow-sm">
                    {s.photos && s.photos.length > 0 && (
                      <div style={{ position: 'relative' }} className="service-img-hover-slider">
                        <Card.Img
                          variant="top"
                          src={s.photos[0].startsWith("http") ? s.photos[0] : `http://localhost:5000/uploads/${s.photos[0]}`}
                          style={{ height: 180, objectFit: "cover", transition: 'opacity 0.2s' }}
                        />
                        {s.photos.length > 1 && (
                          <div className="hover-slider-overlay" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', zIndex: 2, opacity: 0, transition: 'opacity 0.2s' }}>
                            <ImageSlider photos={s.photos} />
                          </div>
                        )}
                      </div>
                    )}
                    <Card.Body>
                      <Card.Title>{s.name}</Card.Title>
                      <Card.Subtitle className="mb-2 text-muted">{s.type}</Card.Subtitle>
                      <Card.Text><strong>Description:</strong> {s.description || "-"}</Card.Text>
                      <Card.Text><strong>Price:</strong> {s.price ? `₹${s.price}` : "-"}</Card.Text>
                      <Card.Text><strong>Location:</strong> {
                        s.city || s.state || s.address
                          ? `${s.city || ''}${s.city && s.state ? ', ' : ''}${s.state || ''}${(s.city || s.state) && s.address ? ', ' : ''}${s.address || ''}`
                          : (s.location || '-')
                      }</Card.Text>
                      <Card.Text><strong>Provider:</strong> {s.provider?.name || '-'}</Card.Text>
                      <Link to={`/service/${s._id}`} className="btn btn-sm btn-outline-primary me-2">Details</Link>
                    </Card.Body>
                  </Card>
                </Col>
              ))}
            </Row>
          )
        )}
      </div>
    </>
  );
}

// Inline image slider for service card hover
function ImageSlider({ photos }) {
  const [index, setIndex] = useState(0);

  useEffect(() => { setIndex(0); }, [photos]);

  useEffect(() => {
    const card = document.querySelector('.service-img-hover-slider');
    if (!card) return;
    const handleMouseEnter = () => {
      const overlay = card.querySelector('.hover-slider-overlay');
      if (overlay) overlay.style.opacity = 1;
    };
    const handleMouseLeave = () => {
      const overlay = card.querySelector('.hover-slider-overlay');
      if (overlay) overlay.style.opacity = 0;
      setIndex(0);
    };
    card.addEventListener('mouseenter', handleMouseEnter);
    card.addEventListener('mouseleave', handleMouseLeave);
    return () => {
      card.removeEventListener('mouseenter', handleMouseEnter);
      card.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [photos]);

  if (!photos || photos.length < 2) return null;
  return (
    <div
      className="service-img-hover-slider"
      onMouseLeave={() => setIndex(0)}
      style={{ width: '100%', height: 180, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}
    >
      <img
        src={photos[index].startsWith('http') ? photos[index] : `http://localhost:5000/uploads/${photos[index]}`}
        alt="service"
        style={{ height: 180, objectFit: 'cover', width: '100%', borderRadius: '0.375rem' }}
      />
      <div className="hover-slider-overlay" style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, opacity: 0, transition: 'opacity 0.3s', pointerEvents: 'none' }} />
      {photos.length > 1 && (
        <div style={{ position: 'absolute', bottom: 8, left: 0, right: 0, display: 'flex', justifyContent: 'center', gap: 6 }}>
          {photos.map((_, i) => (
            <span
              key={i}
              onMouseEnter={() => setIndex(i)}
              style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: i === index ? '#007bff' : '#ddd', cursor: 'pointer', border: '1px solid #fff' }}
            />
          ))}
        </div>
      )}
    </div>
  );
}


export default UserDashboard;
