import React, { useEffect, useState } from "react";
import axios from "axios";
import { Card, Button, Modal, Form, Row, Col, Alert, Spinner } from "react-bootstrap";

const SERVICE_CATEGORIES = [
  "Tutor", "Plumber", "Electrician", "Sweeper", "Salon", "Spa", "Beauty Parlour"
];

const initialForm = {
  name: "",
  description: "",
  price: "",
  category: SERVICE_CATEGORIES[0],
  city: "",
  address: "",
  state: "",
  availability: [], // Array of slot objects
  photos: []
};

function ProviderDashboard() {
  
  
  const handleBookingStatus = async (bookingId, status) => {
    try {
      await axios.post("http://localhost:5000/api/bookings/confirm", { bookingId, status }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchProviderBookings();
    } catch (e) {
      alert('Failed to update booking status.');
    }
  };

  const [services, setServices] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null); 
  const [form, setForm] = useState(initialForm);
  const [photoPreviews, setPhotoPreviews] = useState([]);
  const [alert, setAlert] = useState({ show: false, variant: "", message: "" });
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const token = localStorage.getItem("token");

  
  const [bookings, setBookings] = useState([]);
  const fetchProviderBookings = async () => {
    try {
      const res = await axios.get("http://localhost:5000/api/bookings/provider", {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBookings(res.data);
    } catch (e) {
      setBookings([]);
    }
  };

  
  const fetchMyServices = async () => {
    setLoading(true);
    try {
      const res = await axios.get("http://localhost:5000/api/services/my", {
        headers: { Authorization: `Bearer ${token}` }
      });
      setServices(res.data);
    } catch (e) {
      setAlert({ show: true, variant: "danger", message: "Failed to fetch services." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMyServices();
    fetchProviderBookings();
  }, []);

  
  const handlePhotoChange = (e) => {
    const files = Array.from(e.target.files);
    setForm({ ...form, photos: files });
    setPhotoPreviews(files.map(file => URL.createObjectURL(file)));
  };

  
  const openModal = (service = null) => {
    setEditing(service);
    if (service) {
      setForm({
        name: service.name,
        description: service.description || "",
        price: service.price || "",
        category: service.type || SERVICE_CATEGORIES[0],
        city: service.city || "",
        address: service.address || "",
        state: service.state || "",
        availability: Array.isArray(service.availability) ? service.availability : [],
        photos: [], // photos are handled separately
      });
      setPhotoPreviews(service.photos ? service.photos.map(p => p.startsWith("http") ? p : `/uploads/${p}`) : []);
    } else {
      setForm(initialForm);
      setPhotoPreviews([]);
    }
    setShowModal(true);
  };

  
  const handleSlotChange = (idx, field, value) => {
    const slots = [...form.availability];
    if (field === 'maxCapacity') {
      slots[idx][field] = parseInt(value) || 1;
    } else {
      slots[idx][field] = value;
    }
    setForm({ ...form, availability: slots });
  };
  const addSlot = () => {
    setForm({
      ...form,
      availability: [
        ...form.availability,
        { date: '', time: '', maxCapacity: 1, registeredCount: 0 }
      ]
    });
  };
  const removeSlot = (idx) => {
    const slots = [...form.availability];
    slots.splice(idx, 1);
    setForm({ ...form, availability: slots });
  };


  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setAlert({ show: false, variant: "", message: "" });
    try {
      
      const safeAvailability = form.availability.map(slot => ({
        ...slot,
        maxCapacity: parseInt(slot.maxCapacity) || 1,
        registeredCount: parseInt(slot.registeredCount) || 0
      }));
      const data = new FormData();
      Object.entries({ ...form, availability: safeAvailability }).forEach(([key, value]) => {
        if (key === "photos" && value.length) {
          value.forEach(photo => data.append("photos", photo));
        } else if (key === "availability") {
          data.append("availability", JSON.stringify(value));
        } else {
          data.append(key, value);
        }
      });
      let res;
      if (editing) {
        res = await axios.put(`http://localhost:5000/api/services/update/${editing._id}`,
          data,
          { headers: { Authorization: `Bearer ${token}`, "Content-Type": "multipart/form-data" } }
        );
      } else {
        res = await axios.post("http://localhost:5000/api/services/add",
          data,
          { headers: { Authorization: `Bearer ${token}`, "Content-Type": "multipart/form-data" } }
        );
      }
      setAlert({ show: true, variant: "success", message: `Service ${editing ? "updated" : "added"} successfully!` });
      setShowModal(false);
      fetchMyServices();
    } catch (e) {
      setAlert({ show: true, variant: "danger", message: e.response?.data?.message || "Failed to save service." });
    } finally {
      setLoading(false);
    }
  };


  // Delete service
  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this service?")) return;
    setDeletingId(id);
    try {
      await axios.delete(`http://localhost:5000/api/services/delete/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAlert({ show: true, variant: "success", message: "Service deleted." });
      fetchMyServices();
    } catch (e) {
      setAlert({ show: true, variant: "danger", message: "Failed to delete service." });
    } finally {
      setDeletingId(null);
    }
  };

  // Logout handler
  const handleLogout = () => {
    localStorage.clear();
    window.location.href = "/login";
  };

  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Service Provider Dashboard</h2>
        <Button variant="outline-danger" onClick={handleLogout}>Logout</Button>
      </div>
      <Button variant="primary" className="mb-4" onClick={() => openModal()}>+ Add New Service</Button>
      {alert.show && (
  <Alert
    variant={alert.variant}
    onClose={() => setAlert({ ...alert, show: false })}
    dismissible
    style={{ cursor: 'pointer' }}
    onClick={() => setAlert({ ...alert, show: false })}
  >
    {alert.message}
  </Alert>
)}
      {loading && <div className="text-center"><Spinner animation="border" /></div>}
       {/* Service Booking Summary */}
       <div className="mt-5">
         <h4>Your Services & Bookings</h4>
         <div className="table-responsive mb-4">
           <table className="table table-bordered align-middle">
             <thead className="table-light">
               <tr>
                 <th>Service Name</th>
                 <th>Times Booked</th>
               </tr>
             </thead>
             <tbody>
               {services.map(service => {
                 const count = bookings.filter(b => b.service && b.service._id === service._id).length;
                 return (
                   <tr key={service._id}>
                     <td>{service.name}</td>
                     <td>{count}</td>
                   </tr>
                 );
               })}
             </tbody>
           </table>
         </div>
       </div>
       <h4>Bookings for Your Services</h4>
       <Row xs={1} md={2} lg={3} className="g-4">
        {services.map(service => (
          <Col key={service._id}>
            <Card className="h-100 shadow-sm">
              {service.photos && service.photos.length > 0 && (
                <div style={{ position: 'relative' }} className="service-img-hover-slider">
                  {console.log('Service photos:', service.photos)}
                  <Card.Img
                    variant="top"
                    src={(() => {
                      const p = service.photos[0];
                      if (!p) return '/fallback-image.png';
                      if (typeof p === 'object' && p.name) return `http://localhost:5000/uploads/${p.name}`;
                      if (typeof p === 'string' && p.startsWith('http')) return p;
                      if (typeof p === 'string') return `http://localhost:5000/uploads/${p}`;
                      return '/fallback-image.png';
                    })()}
                    onError={e => { e.target.onerror = null; e.target.src = '/fallback-image.png'; }}
                    style={{ height: 180, objectFit: "cover", transition: 'opacity 0.2s' }}
                  />
                  {service.photos.length > 1 && (
                    <div className="hover-slider-overlay" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', zIndex: 2, opacity: 0, transition: 'opacity 0.2s' }}>
                      <ImageSlider photos={service.photos} />
                    </div>
                  )}
                </div>
              )}
              <Card.Body>
                <Card.Title>{service.name}</Card.Title>
                <Card.Subtitle className="mb-2 text-muted">{service.type}</Card.Subtitle>
                <Card.Text><strong>Description:</strong> {service.description || "-"}</Card.Text>
                <Card.Text><strong>Price:</strong> {service.price ? `₹${service.price}` : "-"}</Card.Text>
                <Card.Text><strong>Location:</strong> {
                  service.city || service.state || service.address
                    ? `${service.city || ''}${service.city && service.state ? ', ' : ''}${service.state || ''}${(service.city || service.state) && service.address ? ', ' : ''}${service.address || ''}`
                    : (service.location || '-')
                }</Card.Text>
                <Card.Text><strong>Available:</strong> {Array.isArray(service.availability) && service.availability.every(slot => typeof slot === 'object' && slot !== null && 'date' in slot && 'time' in slot && 'maxCapacity' in slot) && service.availability.length > 0 ? (
  <div className="mb-0 ps-3">
    <ul>
      {service.availability.map((slot, idx) => (
        <li key={idx}>
          <span>Date: {slot.date ? new Date(slot.date).toLocaleDateString() : '-'}, Time: {slot.time}, Left: {slot.maxCapacity - (slot.registeredCount || 0)} / {slot.maxCapacity}</span>
        </li>
      ))}
    </ul>
  </div>
) : "-"}</Card.Text>
                <div className="d-flex gap-2 mb-3">
                  <Button size="sm" variant="outline-secondary" onClick={() => openModal(service)}>Edit</Button>
                  <Button size="sm" variant="outline-danger" onClick={() => handleDelete(service._id)} disabled={deletingId === service._id}>
                    {deletingId === service._id ? <Spinner size="sm" animation="border" /> : "Delete"}
                  </Button>
                </div>
                {/* BOOKINGS LIST FOR THIS SERVICE */}
                <div className="mt-3 p-2 bg-light border rounded">
                  <h6 className="mb-2">Bookings</h6>
                  <div className="table-responsive">
                    <table className="table table-sm table-bordered table-striped align-middle mb-0">
                      <thead className="table-light">
                        <tr>
                          <th style={{minWidth: 80}}>User</th>
                          <th style={{minWidth: 90}}>Date</th>
                          <th style={{minWidth: 80}}>Time</th>
                          <th style={{minWidth: 90}}>Status</th>
                          <th style={{minWidth: 120}}>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {bookings.filter(b => b.service && b.service._id === service._id).length === 0 ? (
                          <tr><td colSpan="5" className="text-muted">No bookings.</td></tr>
                        ) : (
                          bookings.filter(b => b.service && b.service._id === service._id).map(b => (
                            <tr key={b._id}>
                              <td style={{maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}} title={b.user?.name}>{b.user?.name || '-'}</td>
                              <td>{b.date ? new Date(b.date).toLocaleDateString() : '-'}</td>
                              <td>{b.time || '-'}</td>
                              <td>
                                {b.status === 'confirmed' ? (
                                  <span className="badge bg-success">Confirmed</span>
                                ) : b.status === 'rejected' ? (
                                  <span className="badge bg-danger">Rejected</span>
                                ) : (
                                  <span className="badge bg-secondary">{b.status || '-'}</span>
                                )}
                              </td>
                              <td>
                                {b.status === 'pending' ? (
                                  <>
                                    <Button size="sm" variant="success" onClick={() => handleBookingStatus(b._id, 'confirmed')} className="me-2">Confirm</Button>
                                    <Button size="sm" variant="danger" onClick={() => handleBookingStatus(b._id, 'rejected')}>Reject</Button>
                                  </>
                                ) : null}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Modal for Add/Edit Service */}
      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg" centered>
        <Modal.Header closeButton className="bg-primary text-white">
          <Modal.Title>
            <i className="bi bi-plus-circle me-2"></i>
            {editing ? "Edit Service" : "Add New Service"}
          </Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSubmit} encType="multipart/form-data">
          <Modal.Body style={{ background: '#f8f9fa' }}>
            <Row>
              <Col md={6} className="border-end">
                <Form.Group className="mb-4" controlId="serviceName">
                  <Form.Label className="fw-bold">Service Name</Form.Label>
                  <Form.Control required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g. AC Repair, Home Tutor..." autoFocus />
                </Form.Group>
                <Form.Group className="mb-4" controlId="serviceCategory">
                  <Form.Label className="fw-bold">Category</Form.Label>
                  <Form.Select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} required>
                    <option value="" disabled>Select category</option>
                    {SERVICE_CATEGORIES.map(cat => <option key={cat} value={cat}>{cat}</option>)}
                  </Form.Select>
                </Form.Group>
                <Form.Group className="mb-4" controlId="servicePrice">
                  <Form.Label className="fw-bold">Price (₹)</Form.Label>
                  <Form.Control type="number" min={0} value={form.price} onChange={e => setForm({ ...form, price: e.target.value })} required placeholder="Enter price" />
                  <Form.Text className="text-muted">Set a competitive price for your service.</Form.Text>
                </Form.Group>
                <Form.Group className="mb-4" controlId="formAvailability">
                  <Form.Label className="fw-bold">Available Slots</Form.Label>
                  <div>
                    {form.availability.length === 0 && (
                      <div className="text-muted mb-2">No slots added. Click <strong>Add Slot</strong> to begin.</div>
                    )}
                    {form.availability.map((slot, idx) => (
                      <div key={idx} className="card mb-2 p-2 border border-primary position-relative shadow-sm animate__animated animate__fadeIn" style={{maxWidth: 480}}>
                        <div className="row g-2 align-items-center">
                          <div className="col-md-4 col-12 mb-1 mb-md-0">
                            <Form.Label className="mb-0 small">Date</Form.Label>
                            <Form.Control
                              type="date"
                              value={slot.date ? slot.date.slice(0, 10) : ''}
                              onChange={e => handleSlotChange(idx, 'date', e.target.value)}
                              required
                            />
                          </div>
                          <div className="col-md-3 col-6">
                            <Form.Label className="mb-0 small">Time</Form.Label>
                            <Form.Control
                              type="time"
                              value={slot.time}
                              onChange={e => handleSlotChange(idx, 'time', e.target.value)}
                              required
                            />
                          </div>
                          <div className="col-md-3 col-6">
                            <Form.Label className="mb-0 small">Max Users</Form.Label>
                            <Form.Control
                              type="number"
                              min={1}
                              value={slot.maxCapacity}
                              onChange={e => handleSlotChange(idx, 'maxCapacity', e.target.value)}
                              required
                            />
                          </div>
                          <div className="col-md-2 col-12 text-end pt-md-4 pt-2">
                            <Button variant="outline-danger" size="sm" onClick={() => removeSlot(idx)} title="Remove Slot"><i className="bi bi-trash"></i></Button>
                          </div>
                        </div>
                        <div className="small text-muted mt-1">{slot.date && slot.time ? `Slot: ${new Date(slot.date).toLocaleDateString()} at ${slot.time}` : ''}</div>
                      </div>
                    ))}
                  </div>
                  <Button variant="success" size="sm" onClick={addSlot} className="mt-2"><i className="bi bi-plus-circle me-1"></i> Add Slot</Button>
                  <Form.Text className="text-muted d-block mt-1">Set the date, time, and maximum users for each slot. Remove slots as needed.</Form.Text>
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-4" controlId="serviceDescription">
                  <Form.Label className="fw-bold">Description</Form.Label>
                  <Form.Control as="textarea" rows={4} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} required placeholder="Describe your service, skills, experience, etc." />
                </Form.Group>
                <Row className="mb-4 g-2">
                  <Col md={6}>
                    <Form.Group controlId="serviceCity">
                      <Form.Label className="fw-bold">City</Form.Label>
                      <Form.Control value={form.city} onChange={e => setForm({ ...form, city: e.target.value })} required placeholder="e.g. Mumbai" />
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group controlId="serviceState">
                      <Form.Label className="fw-bold">State</Form.Label>
                      <Form.Control value={form.state} onChange={e => setForm({ ...form, state: e.target.value })} required placeholder="e.g. Maharashtra" />
                    </Form.Group>
                  </Col>
                </Row>
                <Form.Group className="mb-4" controlId="serviceAddress">
                  <Form.Label className="fw-bold">Address</Form.Label>
                  <Form.Control value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} required placeholder="Full address" />
                </Form.Group>
                <Form.Group className="mb-3" controlId="servicePhotos">
                  <Form.Label className="fw-bold">Photos</Form.Label>
                  <Form.Control type="file" accept="image/*" multiple onChange={handlePhotoChange} />
                  <div className="d-flex flex-wrap gap-2 mt-2">
                    {photoPreviews.map((src, idx) => (
                      <div key={idx} style={{position:'relative'}}>
                        <img src={src} alt="preview" style={{ width: 70, height: 70, objectFit: "cover", borderRadius: 8, border: "2px solid #0d6efd", boxShadow: '0 2px 8px #0001' }} />
                      </div>
                    ))}
                  </div>
                  <Form.Text className="text-muted">Upload clear, high-quality images for better visibility.</Form.Text>
                </Form.Group>
              </Col>
            </Row>
          </Modal.Body>
          <Modal.Footer className="bg-light d-flex justify-content-between align-items-center">
            <span className="text-muted small">Fields marked with <span className="text-danger">*</span> are required.</span>
            <div>
              <Button variant="secondary" onClick={() => setShowModal(false)}>
                Cancel
              </Button>
              <Button variant="success" type="submit" className="ms-2">
                <i className={editing ? "bi bi-pencil-square me-1" : "bi bi-plus-circle me-1"}></i>
                {editing ? "Update Service" : "Add Service"}
              </Button>
            </div>
          </Modal.Footer>
        </Form>
      </Modal>
    </div>
  );
}

// Inline image slider for service card hover
function ImageSlider({ photos }) {
  const [index, setIndex] = React.useState(0);
  React.useEffect(() => { setIndex(0); }, [photos]);
  if (photos.length < 2) return null;
  return (
    <div
      onMouseLeave={() => setIndex(0)}
      style={{ width: '100%', height: 180, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}
    >
      <img
        src={photos[index].startsWith('http') ? photos[index] : `http://localhost:5000/uploads/${photos[index]}`}
        alt="service"
        style={{ height: 180, objectFit: 'cover', width: '100%', borderRadius: '0.375rem' }}
      />
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

export default ProviderDashboard;
