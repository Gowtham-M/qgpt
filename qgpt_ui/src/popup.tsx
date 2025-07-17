import React, { useState, useEffect } from "react";
import { Modal, Button, Form, Row, Col } from "react-bootstrap";
import { FiMonitor, FiThermometer, FiMaximize } from "react-icons/fi";
import "./Modal.css";

export interface QGPTSettings {
  llmModel: string;
  temperature: number;
  size: string;
  embeddingModel: string;
}

interface QGPTSettingsModalProps {
  show: boolean;
  onHide: () => void;
  onSave: (settings: QGPTSettings) => void;
  initialSettings: QGPTSettings;
}

const QGPTSettingsModal: React.FC<QGPTSettingsModalProps> = ({
  show,
  onHide,
  onSave,
  initialSettings,
}) => {
  const [llmModel, setLlmModel] = useState(initialSettings.llmModel);
  const [temperature, setTemperature] = useState(initialSettings.temperature);
  const [size, setSize] = useState(initialSettings.size);
  const [embeddingModel, setEmbeddingModel] = useState(
    initialSettings.embeddingModel
  );

  // New state for models fetched from the API
  const [llmModels, setLlmModels] = useState<string[]>([]);
  const [embeddingModels, setEmbeddingModels] = useState<string[]>([]);

  // For the Size slider, map numbers 1-5 to sizes
  const sizeMapping: { [key: number]: string } = {
    1: "XS",
    2: "S",
    3: "M",
    4: "L",
    5: "XL",
  };

  // Convert string size to numeric slider value
  const sizeToNumber = (s: string) => {
    for (const key in sizeMapping) {
      if (sizeMapping[key] === s) return Number(key);
    }
    return 3; // default to "M"
  };

  const [sizeValue, setSizeValue] = useState<number>(
    sizeToNumber(initialSettings.size)
  );

  // When size slider changes, update the string value
  useEffect(() => {
    setSize(sizeMapping[sizeValue]);
  }, [sizeValue, sizeMapping]);

  // Reset local state when the modal is shown or initialSettings change
  useEffect(() => {
    console.log("[QGPTSettingsModal] initialSettings:", initialSettings);
    setLlmModel(initialSettings.llmModel);
    setTemperature(initialSettings.temperature);
    setSize(initialSettings.size);
    setSizeValue(sizeToNumber(initialSettings.size));
    setEmbeddingModel(initialSettings.embeddingModel || "");
  }, [initialSettings, show]);

  useEffect(() => {
    console.log("[QGPTSettingsModal] llmModels:", llmModels);
    console.log("[QGPTSettingsModal] embeddingModels:", embeddingModels);
    console.log("[QGPTSettingsModal] llmModel:", llmModel);
    console.log("[QGPTSettingsModal] embeddingModel:", embeddingModel);
    if (llmModels.length > 0 && !llmModel) {
      setLlmModel(llmModels[0]);
    }
    if (embeddingModels.length > 0 && !embeddingModel) {
      setEmbeddingModel(embeddingModels[0]);
    }
  }, [llmModels, embeddingModels, embeddingModel, llmModel]); // Runs when models update

  // Fetch models once and split into LLM and embedding models
  useEffect(() => {
    fetch("http://localhost:11434/api/tags")
      .then((res) => res.json())
      .then((data) => {
        // Use data.models from the API response
        const models = Array.isArray(data.models) ? data.models : [];
        const filteredLLMModels = models
          .filter((model: any) => !/embed/i.test(model.name))
          .map((model: any) => model.name);
        const embedModels = models
          .filter((model: any) => /embed/i.test(model.name))
          .map((model: any) => model.name);

        console.log("Fetched Models:", models);
        console.log("Filtered LLM Models:", filteredLLMModels);
        console.log("Filtered Embedding Models:", embedModels);

        setLlmModels(filteredLLMModels);
        setEmbeddingModels(embedModels);

        if (!initialSettings.llmModel && filteredLLMModels.length > 0) {
          setLlmModel(filteredLLMModels[0]);
        }
        if (!initialSettings.embeddingModel && embedModels.length > 0) {
          setEmbeddingModel(embedModels[0]);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch models", err);
      });
  }, [initialSettings]);

  const handleSave = () => {
    onSave({ llmModel, temperature, size, embeddingModel });
    onHide();
  };

  // Create a temperature scale array from 0.1 to 2.0 (in increments of 0.1)
  const temperatureScale = Array.from(
    { length: Math.round((2.0 - 0.1) / 0.1) + 1 },
    (_, i) => (0.1 + i * 0.1).toFixed(1)
  );

  return (
    <Modal
      show={show}
      onHide={onHide}
      centered
      backdrop="static"
      size="lg"
      className="qgpt-settings-modal"
    >
      <Modal.Header closeButton>
        <Modal.Title>QGPT Settings</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form>
          {/* LLM Model Selection from API */}
          <Form.Group controlId="llmModel">
            <Form.Label>
              <FiMonitor />
              LLM Model
            </Form.Label>
            <Form.Select
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
            >
              {llmModels.map((model, index) => (
                <option key={index} value={model}>
                  {model}
                </option>
              ))}
            </Form.Select>
          </Form.Group>

          {/* Embedding Model Selection */}
          <Form.Group controlId="embeddingModel">
            <Form.Label>
              <FiMonitor />
              Embedding Model
            </Form.Label>
            <Form.Select
              value={embeddingModel}
              onChange={(e) => setEmbeddingModel(e.target.value)}
            >
              {embeddingModels.map((model, index) => (
                <option key={index} value={model}>
                  {model}
                </option>
              ))}
            </Form.Select>
          </Form.Group>

          {/* Temperature Slider */}
          <Form.Group controlId="temperature" className="mt-4">
            <Row>
              <Col xs={12}>
                <Form.Label className="fw-bold">
                  <FiThermometer style={{ marginRight: "8px" }} />
                  Temperature:{" "}
                  <span className="fw-normal">{temperature.toFixed(1)}</span>
                </Form.Label>
              </Col>
              <Col xs={12}>
                <div style={{ position: "relative" }}>
                  <Form.Range
                    min={0.1}
                    max={2}
                    step={0.1}
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  />
                  <div
                    style={{
                      position: "absolute",
                      top: "22px",
                      left: 0,
                      width: "100%",
                    }}
                  >
                    <div
                      className="d-flex justify-content-between"
                      style={{ fontSize: "0.75rem" }}
                    >
                      {temperatureScale.map((val, index) => (
                        <span key={index}>{val}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </Col>
            </Row>
          </Form.Group>

          {/* Size Slider */}
          <Form.Group controlId="size" className="mt-4">
            <Row>
              <Col xs={12}>
                <Form.Label className="fw-bold">
                  <FiMaximize style={{ marginRight: "8px" }} />
                  Size of Response: <span className="fw-normal">{size}</span>
                </Form.Label>
              </Col>
              <Col xs={12}>
                <Form.Range
                  min={1}
                  max={5}
                  step={1}
                  value={sizeValue}
                  onChange={(e) => setSizeValue(parseInt(e.target.value))}
                />
                <div className="slider-labels">
                  {Object.entries(sizeMapping).map(([num, label]) => (
                    <span key={num}>{label}</span>
                  ))}
                </div>
              </Col>
            </Row>
          </Form.Group>
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Cancel
        </Button>
        <Button variant="primary" onClick={handleSave}>
          Save Settings
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default QGPTSettingsModal;
