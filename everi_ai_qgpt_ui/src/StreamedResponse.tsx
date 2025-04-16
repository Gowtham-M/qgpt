import React, { useState, useEffect } from "react";
import ReactShowdown from "react-showdown"

const StreamedResponse = ({ fullResponse, speed }) => {
  const [displayText, setDisplayText] = useState("");

  useEffect(() => {
    if (!fullResponse) return;
    
    let index = 0;
    const intervalId = setInterval(() => {
      index++;
      setDisplayText(fullResponse.slice(0, index));
      if (index >= fullResponse.length) {
        clearInterval(intervalId);
      }
    }, speed);

    return () => clearInterval(intervalId);
  }, [fullResponse, speed]);

  return (
    <div style={{ margin: "0", padding: "0", lineHeight: "1.2" }}>
                          <ReactShowdown markdown={displayText}/>
                        </div>
  );
};

export default StreamedResponse;
