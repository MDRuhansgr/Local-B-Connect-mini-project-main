import React, { useState } from "react";
import axios from "axios";
import { useNavigate, Link } from "react-router-dom";
import { Card, Button, Form, Alert, Modal } from "react-bootstrap";
import Loading from "../Loading";

function Register() {
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "user" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await axios.post("http://localhost:5000/api/auth/register", form);
      setSuccess("Registration successful! You can now login.");
      setTimeout(() => navigate("/login"), 1500);
    } catch (err) {
      setError(err.response?.data?.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading text="Registering..." />;

  return (
    <div className="d-flex justify-content-center align-items-center min-vh-100 bg-light">
      <Card style={{ width: '100%', maxWidth: 450 }} className="shadow p-4">
        <Card.Body>
          <h2 className="mb-4 text-center">Create Account</h2>
          {error && <Alert variant="danger">{error}</Alert>}
          {success && <Alert variant="success">{success}</Alert>}
          <Form onSubmit={handleSubmit} autoComplete="off">
            <Form.Group className="mb-3" controlId="registerName">
              <Form.Label>Name</Form.Label>
              <Form.Control
                type="text"
                placeholder="Enter your name"
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                required
              />
            </Form.Group>
            <Form.Group className="mb-3" controlId="registerEmail">
              <Form.Label>Email</Form.Label>
              <Form.Control
                type="email"
                placeholder="Enter your email"
                value={form.email}
                onChange={e => setForm({ ...form, email: e.target.value })}
                required
              />
            </Form.Group>
            <Form.Group className="mb-3" controlId="registerPassword">
              <Form.Label>Password</Form.Label>
              <Form.Control
                type="password"
                placeholder="Enter password"
                value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
                required
                minLength={6}
              />
            </Form.Group>

            <Form.Group className="mb-3" controlId="registerRole">
              <Form.Label>Register as</Form.Label>
              <div className="d-flex gap-3">
                <Form.Check
                  type="radio"
                  label={<span>Customer <span className="text-muted small">(Book services, find providers)</span></span>}
                  name="role"
                  id="customer-radio"
                  value="user"
                  checked={form.role === "user"}
                  onChange={e => setForm({ ...form, role: e.target.value })}
                  required
                />
                <Form.Check
                  type="radio"
                  label={<span>Service Provider <span className="text-muted small">(Offer your services)</span></span>}
                  name="role"
                  id="provider-radio"
                  value="provider"
                  checked={form.role === "provider"}
                  onChange={e => setForm({ ...form, role: e.target.value })}
                  required
                />
              </div>
            </Form.Group>
            <Button variant="primary" type="submit" className="w-100" disabled={loading}>
              Register
            </Button>
          </Form>
          <div className="mt-3 text-center">
            <span>Already have an account? </span>
            <Link to="/login">Login here</Link>
          </div>
        </Card.Body>
      </Card>
    </div>
  );
}

export default Register;
