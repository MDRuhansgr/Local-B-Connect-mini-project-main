import React, { useState } from "react";
import axios from "axios";
import { useNavigate, Link } from "react-router-dom";
import { Card, Button, Form, Alert, ToggleButtonGroup, ToggleButton } from "react-bootstrap";

function Login() {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await axios.post("http://localhost:5000/api/auth/login", form);
      const { token, userType, userId } = res.data;
      localStorage.setItem("token", token);
      localStorage.setItem("userType", userType);
      localStorage.setItem("userId", userId);

      if (userType === "provider") {
        navigate("/provider-dashboard");
      } else if (userType === "user") {
        navigate("/user-dashboard");
      } else {
        setError("Unknown user type. Please contact support.");
      }
    } catch (err) {
      setError(err.response?.data?.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="d-flex justify-content-center align-items-center min-vh-100 bg-light">
      <Card style={{ width: '100%', maxWidth: 400 }} className="shadow p-4">
        <Card.Body>
          <h2 className="mb-4 text-center">Sign In</h2>
          {error && <Alert variant="danger">{error}</Alert>}
          <Form onSubmit={handleLogin} autoComplete="off">
            <Form.Group className="mb-3" controlId="loginEmail">
              <Form.Label>Email</Form.Label>
              <Form.Control
                type="email"
                placeholder="Enter email"
                value={form.email}
                onChange={e => setForm({ ...form, email: e.target.value })}
                required
              />
            </Form.Group>
            <Form.Group className="mb-3" controlId="loginPassword">
              <Form.Label>Password</Form.Label>
              <Form.Control
                type="password"
                placeholder="Password"
                value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
                required
                minLength={6}
              />
            </Form.Group>

            <Button variant="success" type="submit" className="w-100" disabled={loading}>
              {loading ? "Signing in..." : "Sign In"}
            </Button>
          </Form>
          <div className="mt-3 text-center">
            <span>Don't have an account? </span>
            <Link to="/register">Sign up</Link>
          </div>
        </Card.Body>
      </Card>
    </div>
  );
}

export default Login;
