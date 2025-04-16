import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Form, Card, Col, Row } from "react-bootstrap";
import 'bootstrap/dist/css/bootstrap.min.css'; // Ensure Bootstrap is imported

const Login: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem("userEmail", email);
    // Redirect to the chat page with email passed as state
    navigate("/chat", { state: { email } });
  };

  return (
    <div className="container d-flex justify-content-center align-items-center" style={{ height: "100vh" }}>
      <Row className="w-100 d-flex justify-content-center">
        {/* Outer Welcome Card */}
        <Col xs={12} className="mb-4">
          <Card className="shadow-lg border-0 rounded-4" style={{ backgroundColor: "#f0f8ff", padding: "2rem" }}>
            <Card.Body className="text-center">
              <Card.Title className="display-3 text-primary">Welcome to QantumData Leap GPT</Card.Title>
              <Card.Text className="lead mb-4">
                Your personal AI assistant, ready to help you at any time. Log in below to get started!
              </Card.Text>
            </Card.Body>
          </Card>
        </Col>

        {/* Inner Login Form Card */}
        <Col xs={12} md={4} className="d-flex justify-content-center">
          <Card className="shadow-lg border-0 rounded-4 p-4" style={{ maxWidth: "400px", width: "100%" }}>
            <h3 className="text-center mb-4">Login</h3>
            <Form onSubmit={handleSubmit}>
              <Form.Group className="mb-3" controlId="formEmail">
                <Form.Label>Email</Form.Label>
                <Form.Control
                  type="email"
                  placeholder="Enter Everi email"
                  value={email}
                  required
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Form.Group>

              <Form.Group className="mb-3" controlId="formPassword">
                <Form.Label>Password</Form.Label>
                <Form.Control
                  type="password"
                  placeholder="Password"
                  value={password}
                  required
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Form.Group>

              <Button variant="primary" type="submit" className="w-100 mt-4">
                Login
              </Button>
            </Form>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Login;
