import React from "react";
import "./style.css"; // Import the CSS file

interface EmailLogoProps {
  email: string;
  className?: string; // Make class name customizable
}

const EmailLogo: React.FC<EmailLogoProps> = ({ email, className = "email-logo" }) => {
  // Extract initials from email
  const getInitials = (email: string): string => {
    if (!email) return "";
    const parts = email.split("@")[0].split("."); // Extract part before '@' and split by dots
    return parts.map((word) => word.charAt(0).toUpperCase()).join(""); // Extract initials
  };

  return <div className={className}>{getInitials(email)}</div>;
};

export default EmailLogo;
