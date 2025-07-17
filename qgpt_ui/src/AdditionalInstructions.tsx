import React, { useState } from "react";
import { Dropdown } from "react-bootstrap";

interface Prompt {
  id: number;
  name: string;
  content: string;
  description: string;
  path: string;
}

interface AdditionalInstructionsProps {
  prompts: Prompt[];
  systemPromptInput: string;
  setSystemPromptInput: (value: string) => void;
}

const AdditionalInstructions: React.FC<AdditionalInstructionsProps> = ({
  prompts,
  systemPromptInput,
  setSystemPromptInput,
}) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const [filteredPrompts, setFilteredPrompts] = useState<Prompt[]>([]);

  // Handle textarea input
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setSystemPromptInput(value);

    // Show dropdown only when `/` is the last character
    if (value.endsWith("/")) {
      setShowDropdown(true);
      setFilteredPrompts(prompts);
    } else {
      setShowDropdown(false);
    }
  };

  // Insert selected prompt into textarea
  const insertPrompt = (prompt: Prompt) => {
    // Replace the last `/` with the selected prompt content
    const newInput = systemPromptInput.replace(/\/$/, "") + prompt.content;
    setSystemPromptInput(newInput);
    setShowDropdown(false); // Close dropdown after selection
  };


  return (
    <div className="additional-instructions-wrapper curvy-chat-input">
      <textarea
        className="form-control curvy-textarea"
        placeholder="Enter Additional Instructions..."
        rows={3}
        value={systemPromptInput}
        onChange={handleInputChange}
      ></textarea>

      {showDropdown && (
        <Dropdown className="position-absolute w-100" show>
          <Dropdown.Menu className="w-100">
            {filteredPrompts.map((prompt) => (
              <Dropdown.Item
                key={prompt.id}
                onClick={() => insertPrompt(prompt)}
              >
                {prompt.path}
              </Dropdown.Item>
            ))}
          </Dropdown.Menu>
        </Dropdown>
      )}
    </div>
  );
};

export default AdditionalInstructions;
