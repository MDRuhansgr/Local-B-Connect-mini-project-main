import React from "react";
import { Navbar, Nav, Container, Button } from "react-bootstrap";
import { Link, useNavigate } from "react-router-dom";

const AppNavbar = () => {
  const navigate = useNavigate();
  const isLoggedIn = Boolean(localStorage.getItem("token"));
  const userType = localStorage.getItem("userType");

  const handleLogout = () => {
    localStorage.clear();
    navigate("/login");
  };

  return (
    <Navbar bg="white" expand="lg" sticky="top" className="shadow-sm mb-3">
      <Container>
        <Navbar.Brand as={Link} to="/" className="fw-bold text-primary">
          Local-B-Connect
        </Navbar.Brand>
        <Navbar.Toggle aria-controls="main-navbar-nav" />
        <Navbar.Collapse id="main-navbar-nav">
          <Nav className="ms-auto align-items-center gap-2">
            <Nav.Link as={Link} to="/">Home</Nav.Link>
            {!isLoggedIn && (
              <>
                <Nav.Link as={Link} to="/login">Login</Nav.Link>
                <Nav.Link as={Link} to="/register">Sign Up</Nav.Link>
              </>
            )}
            {isLoggedIn && (
              <>
                {userType === "provider" ? (
                  <Nav.Link as={Link} to="/provider-dashboard">Dashboard</Nav.Link>
                ) : (
                  <Nav.Link as={Link} to="/user-dashboard">Dashboard</Nav.Link>
                )}
                <Button variant="outline-danger" size="sm" onClick={handleLogout} className="ms-2">
                  Logout
                </Button>
              </>
            )}
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default AppNavbar;
