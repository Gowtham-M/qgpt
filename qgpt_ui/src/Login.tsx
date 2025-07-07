import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Form, Card, Col, Row, Container } from "react-bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";
import "./Login.css"; // We'll create this file

const Login: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem("userEmail", email);
    navigate("/chat", { state: { email } });
  };

  return (
    <div className="login-page">
      <Container fluid className="login-container">
        <Row className="align-items-center justify-content-center">
          <Col xs={12} md={10} lg={8} xl={6}>
            {/* Welcome Header */}
            <div className="welcome-header text-center mb-3">
              <div className="logo-container mb-2">
                <div className="logo-circle">
                  <svg width="60" height="60" viewBox="0 0 60 60" fill="none">
                    <circle cx="30" cy="30" r="25" fill="url(#gradient)" />
                    <path
                      d="M20 25L25 30L40 20"
                      stroke="white"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <defs>
                      <linearGradient
                        id="gradient"
                        x1="0%"
                        y1="0%"
                        x2="100%"
                        y2="100%"
                      >
                        <stop offset="0%" stopColor="#667eea" />
                        <stop offset="100%" stopColor="#764ba2" />
                      </linearGradient>
                    </defs>
                  </svg>
                </div>
              </div>
              <h1 className="welcome-title">
                Welcome to Quantum Data Leap GPT
              </h1>
              <p className="welcome-subtitle">
                Your intelligent AI assistant for data analysis, insights, and
                more.
                <br />
                Sign in to unlock the power of quantum-enhanced conversations.
              </p>
            </div>

            {/* Login Form */}
            <Card className="login-card">
              <Card.Body className="p-5">
                <div className="text-center mb-4">
                  <h3 className="login-title">Sign In</h3>
                  <p className="login-subtitle">Access your AI assistant</p>
                </div>

                <Form onSubmit={handleSubmit}>
                  <Form.Group className="mb-4">
                    <Form.Label className="form-label">
                      Email Address
                    </Form.Label>
                    <Form.Control
                      type="email"
                      placeholder="Enter your email"
                      value={email}
                      required
                      onChange={(e) => setEmail(e.target.value)}
                      className="form-input"
                    />
                  </Form.Group>

                  <Form.Group className="mb-4">
                    <Form.Label className="form-label">Password</Form.Label>
                    <Form.Control
                      type="password"
                      placeholder="Enter your password"
                      value={password}
                      required
                      onChange={(e) => setPassword(e.target.value)}
                      className="form-input"
                    />
                  </Form.Group>

                  <Button type="submit" className="login-button w-100">
                    <span>Sign In</span>
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 20 20"
                      fill="none"
                      className="ms-2"
                    >
                      <path
                        d="M4 10h12m-6-6l6 6-6 6"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </Button>
                </Form>
              </Card.Body>
            </Card>

            {/* Footer */}
            <div className="login-footer text-center mt-2">
              <p className="footer-text">
                Powered by <strong>Quantum Data Leap</strong> Technology
              </p>
            </div>
          </Col>
        </Row>
      </Container>
    </div>
  );
};

export default Login;
