import React, { useEffect, useState } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";
import { Carousel, Modal, Button, Form, Alert, Spinner } from "react-bootstrap";

function ServiceDetails() {
  const { id } = useParams();
  const [service, setService] = useState({});
  const [comment, setComment] = useState("");
  const [rating, setRating] = useState(5);
  const [bookingDate, setBookingDate] = useState("");
  const [bookingTime, setBookingTime] = useState("");
  const [bookingSuccess, setBookingSuccess] = useState("");
  const [bookingError, setBookingError] = useState("");
  const [showImgModal, setShowImgModal] = useState(false);
  const [imgIndex, setImgIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const token = localStorage.getItem("token");

  const fetchService = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`http://localhost:5000/api/services/details/${id}`);
      setService(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchService();
  }, []);

  const handleReview = async (e) => {
    e.preventDefault();
    await axios.post(`http://localhost:5000/api/services/review/${id}`,
      { comment, rating },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    fetchService();
    setComment(""); setRating(5);
  };

  const handleBooking = async (e) => {
    e.preventDefault();
    setBookingSuccess("");
    setBookingError("");
    try {
      await axios.post(`http://localhost:5000/api/bookings/create`, {
        serviceId: id,
        date: bookingDate,
        time: bookingTime,
        amount: service.price || 0
      }, { headers: { Authorization: `Bearer ${token}` } });
      setBookingSuccess("Booking successful! You will be contacted soon.");
      setBookingDate("");
      setBookingTime("");
    } catch (err) {
      setBookingError(err.response?.data?.message || "Booking failed. Try another slot.");
    }
  };

  const availableSlots = Array.isArray(service.availability) ? service.availability : [];
  const photos = service.photos || [];

  return (
    <div className="container mt-4">
      {loading ? (
        <div className="text-center py-5"><Spinner animation="border" /></div>
      ) : (
        <>
          <div className="row">
            <div className="col-md-6">
              
              {photos.length > 0 ? (
                <>
                  <Carousel interval={null} onSelect={i => setImgIndex(i)} activeIndex={imgIndex} className="mb-3" style={{ borderRadius: 12, boxShadow: '0 2px 16px #eee' }}>
                    {photos.map((p, i) => (
                      <Carousel.Item key={i}>
                        <img
                          src={(() => {
                            if (!p) return '/fallback-image.png';
                            if (typeof p === 'object' && p.name) return `http://localhost:5000/uploads/${p.name}`;
                            if (typeof p === 'string' && p.startsWith('http')) return p;
                            if (typeof p === 'string') return `http://localhost:5000/uploads/${p}`;
                            return '/fallback-image.png';
                          })()}
                          onError={e => { e.target.onerror = null; e.target.src = '/fallback-image.png'; }}
                          alt={`Service ${i + 1}`}
                          className="d-block w-100"
                          style={{ height: 320, objectFit: 'cover', borderRadius: 12, cursor: 'pointer' }}
                          onClick={() => { setImgIndex(i); setShowImgModal(true); }}
                        />
                      </Carousel.Item>
                    ))}
                  </Carousel>
                  
                  <Modal show={showImgModal} onHide={() => setShowImgModal(false)} centered size="lg">
                    <Modal.Body className="text-center p-0">
                      <img
                        src={(() => {
                          const p = photos[imgIndex];
                          if (!p) return '/fallback-image.png';
                          if (typeof p === 'object' && p.name) return `http://localhost:5000/uploads/${p.name}`;
                          if (typeof p === 'string' && p.startsWith('http')) return p;
                          if (typeof p === 'string') return `http://localhost:5000/uploads/${p}`;
                          return '/fallback-image.png';
                        })()}
                        onError={e => { e.target.onerror = null; e.target.src = '/fallback-image.png'; }}
                        alt="Zoomed Service"
                        style={{ width: '100%', maxHeight: 500, objectFit: 'contain', borderRadius: 12 }}
                      />
                    </Modal.Body>
                  </Modal>
                </>
              ) : (
                <div className="bg-light text-center py-5 rounded mb-3">No photos available</div>
              )}
            </div>
            <div className="col-md-6">
              <h2>{service.name}</h2>
              <p className="mb-1"><strong>Category:</strong> {service.type} {service.subtype && <>- {service.subtype}</>}</p>
              <p className="mb-1"><strong>Location:</strong> {service.city || service.location || "-"}</p>
              <p className="mb-1"><strong>Provider:</strong> {service.provider?.name || "-"}</p>
              <p className="mb-1"><strong>Contact:</strong> {service.provider?.contact || "-"}</p>
              <p className="mb-1"><strong>Price:</strong> ₹{service.price || "-"}</p>
              <p className="mb-1"><strong>⭐ Rating:</strong> {service.rating || "No ratings yet"}</p>
              <p className="mb-1"><strong>Description:</strong> {service.description || "-"}</p>
              
              <div className="mb-3">
                <strong>Available Slots:</strong>
                {availableSlots.length > 0 ? (
                  <ul className="list-group mt-2 mb-0">
                    {availableSlots.map((slot, idx) => (
                      <li key={idx} className="list-group-item d-flex justify-content-between align-items-center">
                        <span>
                          <strong>Date:</strong> {slot.date ? new Date(slot.date).toLocaleDateString() : '-'}<br/>
                          <strong>Time:</strong> {slot.time}<br/>
                          <strong>Available:</strong> {slot.maxCapacity - (slot.registeredCount || 0)} / {slot.maxCapacity}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-muted ms-2">No slots set</span>
                )}
              </div>
              
              <div className="mb-3">
                <h5>Book this Service</h5>
                <Form onSubmit={handleBooking} className="row g-2">
                  <div className="col-6">
                    <Form.Label>Date</Form.Label>
                    <Form.Control type="date" required value={bookingDate} onChange={e => setBookingDate(e.target.value)} min={new Date().toISOString().split('T')[0]} />
                  </div>
                  <div className="col-6">
                    <Form.Label>Time</Form.Label>
                    <Form.Control type="time" required value={bookingTime} onChange={e => setBookingTime(e.target.value)} />
                  </div>
                  <div className="col-12">
                    <Button type="submit" variant="success" className="w-100 mt-2">Book Now</Button>
                  </div>
                </Form>
                {bookingSuccess && <Alert variant="success" className="mt-2">{bookingSuccess}</Alert>}
                {bookingError && <Alert variant="danger" className="mt-2">{bookingError}</Alert>}
              </div>
            </div>
          </div>
          <hr />
          {/* Reviews Section */}
          <div className="row mt-4">
            <div className="col-md-6">
              <h5 className="mb-3">Leave a Review</h5>
              <form onSubmit={handleReview}>
                <textarea className="form-control mb-2" placeholder="Comment" rows={3}
                  value={comment} onChange={(e) => setComment(e.target.value)} required />
                <select className="form-control mb-2"
                  value={rating} onChange={(e) => setRating(e.target.value)}>
                  {[5, 4, 3, 2, 1].map(r => <option key={r} value={r}>{r} Star</option>)}
                </select>
                <button className="btn btn-primary">Submit Review</button>
              </form>
            </div>
            <div className="col-md-6">
              <h5 className="mb-3">All Reviews</h5>
              <ul className="list-group">
                {service.reviews?.length === 0 && <li className="list-group-item text-muted">No reviews yet.</li>}
                {service.reviews?.map((r, idx) => (
                  <li key={idx} className="list-group-item">
                    <div className="fw-bold">{r.user?.name || "User"} <span className="text-warning">{"★".repeat(r.rating)}{"☆".repeat(5 - r.rating)}</span></div>
                    <div>{r.comment}</div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default ServiceDetails;
