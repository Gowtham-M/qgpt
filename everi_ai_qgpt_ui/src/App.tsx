import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Chat from "./chat.tsx";
import Login from "./Login.tsx";
import "bootstrap/dist/css/bootstrap.min.css"; // Bootstrap import
import "./App.css";
 
const App: React.FC = () => {
  return (
    <Router>
      <div>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </div>
    </Router>
  );
};
 
export default App;