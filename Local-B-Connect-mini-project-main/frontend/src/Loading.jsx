import React from "react";
import { Spinner } from "react-bootstrap";

let logoSrc = null;
try {
  logoSrc = require("../assets/logo.png");
} catch (e) {
  logoSrc = null;
}

const Loading = ({ text = "Loading..." }) => (
  <div style={{
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    background: "rgba(255,255,255,0.9)",
    zIndex: 9999
  }}>
    {logoSrc && <img src={logoSrc} alt="Logo" style={{ width: 80, marginBottom: 24 }} />}
    <Spinner animation="border" variant="primary" style={{ width: 48, height: 48 }} />
    <div className="mt-3 text-primary fw-bold">{text}</div>
  </div>
);

export default Loading;
