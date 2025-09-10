import React from 'react';
import { Link } from 'react-router-dom';
import { Container, Row, Col, Button, Card } from 'react-bootstrap';
import { FaTools, FaSearch, FaStar, FaUsers, FaHandshake } from 'react-icons/fa';
import AppNavbar from '../Navbar';
import './Home.css';

const Home = () => {
  return (
    <>
      <AppNavbar />
      <div className="home-page">
        
        <section className="hero-section py-5 bg-light">
          <Container>
            <Row className="align-items-center">
              <Col lg={6} className="mb-4 mb-lg-0">
                <h1 className="display-4 fw-bold mb-4 text-primary">Connecting You with Local Service Providers</h1>
                <p className="lead mb-4">
                  Find trusted professionals for all your service needs. Quick, reliable, and hassle-free solutions at your fingertips.
                </p>
                <div className="d-flex gap-3">
                  <Button as={Link} to="/register" variant="primary" size="lg" className="px-4">
                    Get Started
                  </Button>
                  <Button as={Link} to="/login" variant="outline-primary" size="lg" className="px-4">
                    Sign In
                  </Button>
                </div>
              </Col>
              <Col lg={6}>
                <img 
                  src="https://images.unsplash.com/photo-1552664730-d307ca884978?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=1470&q=80" 
                  alt="Professional Services" 
                  className="img-fluid rounded-3 shadow"
                />
              </Col>
            </Row>
          </Container>
        </section>

      
      <section className="features-section py-5">
        <Container>
          <h2 className="text-center mb-5">Why Choose Local-B-Connect?</h2>
          <Row className="g-4">
            <Col md={4}>
              <Card className="h-100 border-0 shadow-sm p-4 text-center">
                <div className="feature-icon mb-3">
                  <FaSearch size={40} className="text-primary" />
                </div>
                <Card.Title>Easy to Find</Card.Title>
                <Card.Text>
                  Quickly find local service providers in your area with our intuitive search.
                </Card.Text>
              </Card>
            </Col>
            <Col md={4}>
              <Card className="h-100 border-0 shadow-sm p-4 text-center">
                <div className="feature-icon mb-3">
                  <FaStar size={40} className="text-warning" />
                </div>
                <Card.Title>Verified Professionals</Card.Title>
                <Card.Text>
                  All providers are vetted and reviewed by our community.
                </Card.Text>
              </Card>
            </Col>
            <Col md={4}>
              <Card className="h-100 border-0 shadow-sm p-4 text-center">
                <div className="feature-icon mb-3">
                  <FaHandshake size={40} className="text-success" />
                </div>
                <Card.Title>Hassle-Free</Card.Title>
                <Card.Text>
                  Simple booking and secure payments all in one place.
                </Card.Text>
              </Card>
            </Col>
          </Row>
        </Container>
      </section>

      {/* Call to Action */}
      <section className="cta-section py-5 bg-primary text-white">
        <Container className="text-center">
          <h2 className="mb-4">Ready to get started?</h2>
          <p className="lead mb-4">Join thousands of satisfied customers today.</p>
          <Button as={Link} to="/register" variant="light" size="lg" className="px-4">
            Sign Up Now
          </Button>
        </Container>
      </section>
    </div>
    </>
  );
};

export default Home;
