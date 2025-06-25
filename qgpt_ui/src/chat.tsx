import React, { useState, useEffect, useRef, useCallback } from "react";
import { useChatHandlers } from "./api.ts";
import StreamedResponse from "./StreamedResponse.tsx";
import ReactShowdown from "react-showdown";
import "./style.css";
import "./maps.css";
import { useLocation, useNavigate } from "react-router-dom";
import { Navbar, Container, Nav, Button } from "react-bootstrap";
import QGPTSettingsModal from "./popup.tsx";
import ChatSidebar from "./sidebar/ChatSidebar.tsx";
import {
  FiCopy,
  FiArrowDownCircle,
  FiArrowLeft,
  FiArrowRight,
  FiCheck,
  FiMonitor,
  FiThermometer,
  FiMaximize,
  FiSettings,
  FiTrash2,
  FiCheckSquare,
  FiSquare,
  FiMic,
  FiMicOff,
  FiImage, // Add FiImage for image upload icon
  FiMap, // Add FiMap for maps feature
} from "react-icons/fi";
import EmailLogo from "./EmailLogo.tsx";
import PromptPanel from "./PromptPanel.tsx";
import AdditionalInstructions from "./AdditionalInstructions.tsx";
import MapsComponent from "./MapsComponent.tsx";
import GdriveImg from "./assets/gdrive.png";
import OneDriveImg from "./assets/one-drive.png";
import Fiseclogo from "./Fisec_QGPT_Logo.png";

// TypeScript declarations for Speech Recognition API
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  onresult: (event: any) => void;
  onerror: (event: any) => void;
  onend: () => void;
}

// Load messages from localStorage by key mode and chatid
function loadCachedMessages(keySuffix: string) {
  try {
    const data = localStorage.getItem(`chatHistory_${keySuffix}`);
    if (!data) return null;
    return JSON.parse(data);
  } catch (err) {
    console.error("Failed to parse cached data", err);
    return null;
  }
}

// Save messages to localStorage by key
function saveCachedMessages(messages: any, keySuffix: string) {
  try {
    localStorage.setItem(`chatHistory_${keySuffix}`, JSON.stringify(messages));
  } catch (err) {
    console.error("Failed to store chat messages in localStorage", err);
  }
}

const Chat: React.FC = () => {
  // Import default mode from settings if available
  const DEFAULT_MODE = "RAG"; // fallback
  // Try to get from window/global if injected, else fallback
  let defaultMode = DEFAULT_MODE;
  if (window && window.qgptSettings && window.qgptSettings.default_mode) {
    defaultMode = window.qgptSettings.default_mode;
  }

  // Patch: add setMode from useChatHandlers
  const {
    messages,
    setMessages, // <-- add this to the destructure
    input,
    setInput,
    mode,
    setMode, // <-- add this to the destructure
    files,
    selectedFiles,
    fileInputRef,
    fileLoading,
    messageLoading,
    sidebarLeftHidden,
    sidebarRightHidden,
    handleSendMessage,
    handleRetry,
    handleUndo,
    handleModeChange,
    toggleFileSelection,
    handleDeselectFile,
    handleDeleteSelectedFiles,
    handleDeleteFile,
    currentChatId,
    setCurrentChatId,
    onFileChange,
    toggleSidebarLeft,
    toggleSidebarRight,
    handleStopMessage,
    handleClearChat,
    systemPromptInput,
    setSystemPromptInput, // <-- add this to the destructure
    setSelectedFiles,
    handleConnectGoogleDrive,
    handleConnectOneDrive,
  } = useChatHandlers();

  const [showLogout, setShowLogout] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const email = location.state?.email || localStorage.getItem("userEmail");
  const [showInstructions, setShowInstructions] = useState(true);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const responseBoxRef = useRef<HTMLDivElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const [folders, setFolders] = useState<
    {
      id: number;
      name: string;
      prompts: {
        id: number;
        name: string;
        content: string;
        description: string;
      }[];
    }[]
  >(() => {
    const savedFolders = localStorage.getItem("folders");
    return savedFolders ? JSON.parse(savedFolders) : [];
  });

  const [prompts, setPrompts] = useState<
    {
      id: number;
      name: string;
      content: string;
      description: string;
    }[]
  >(() => {
    const savedPrompts = localStorage.getItem("prompts");
    return savedPrompts ? JSON.parse(savedPrompts) : [];
  });

  const [totalPrompts, setTotalPrompts] = useState<
    {
      id: number;
      name: string;
      content: string;
      description: string;
      path: string;
    }[]
  >(() => {
    const savedTotalPrompts = localStorage.getItem("totalPrompts");
    return savedTotalPrompts ? JSON.parse(savedTotalPrompts) : [];
  });
  // Update total prompts (to include paths)
  const updateTotalPrompts = useCallback(() => {
    // Only include root-level prompts and folder prompts, without duplicating them
    const folderPrompts = folders.flatMap((folder) =>
      folder.prompts.map((prompt) => ({
        ...prompt,
        path: `${folder.name}/${prompt.name}`, // Store folder path
      }))
    );

    const updatedTotalPrompts = [
      ...prompts.map((prompt) => ({
        ...prompt,
        path: prompt.name, // Root prompts have no folder
      })),
      ...folderPrompts,
    ];

    setTotalPrompts(updatedTotalPrompts);
  }, [folders, prompts]);

  useEffect(() => {
    updateTotalPrompts();
  }, [updateTotalPrompts]);

  // Persist folders, prompts, and totalPrompts to localStorage
  useEffect(() => {
    localStorage.setItem("folders", JSON.stringify(folders));
    localStorage.setItem("prompts", JSON.stringify(prompts));
    localStorage.setItem("totalPrompts", JSON.stringify(totalPrompts));
  }, [folders, prompts, totalPrompts]);

  const addPrompt = (newPrompt) => {
    // Check if prompt already exists in folders
    const existingPrompt = prompts.find((prompt) => prompt.id === newPrompt.id);
    if (!existingPrompt) {
      setPrompts([...prompts, newPrompt]);
    }
  };

  const addFolder = (name: string) => {
    if (name) {
      setFolders([...folders, { id: Date.now(), name, prompts: [] }]);
    }
  };

  const addPromptToFolder = (folderId: number, newPrompt) => {
    setFolders((prevFolders) =>
      prevFolders.map((folder) =>
        folder.id === folderId
          ? { ...folder, prompts: [...folder.prompts, newPrompt] }
          : folder
      )
    );
    // No need to add the prompt to the root `prompts` list in this case
    updateTotalPrompts();
  };

  // Update a prompt
  const updatePrompt = (updatedPrompt) => {
    setPrompts((prev) =>
      prev.map((p) => (p.id === updatedPrompt.id ? updatedPrompt : p))
    );
    setFolders((prevFolders) =>
      prevFolders.map((folder) => ({
        ...folder,
        prompts: folder.prompts.map((prompt) =>
          prompt.id === updatedPrompt.id ? updatedPrompt : prompt
        ),
      }))
    );
  };

  // Update folder name
  const updateFolder = (folderId: number, newName: string) => {
    setFolders((prevFolders) =>
      prevFolders.map((folder) =>
        folder.id === folderId ? { ...folder, name: newName } : folder
      )
    );
  };

  // Delete a prompt
  const deletePrompt = (promptId: number) => {
    setPrompts(prompts.filter((prompt) => prompt.id !== promptId));
    setFolders((folders) =>
      folders.map((folder) => ({
        ...folder,
        prompts: folder.prompts.filter((prompt) => prompt.id !== promptId),
      }))
    );
  };

  // Delete a folder
  const deleteFolder = (folderId: number) => {
    setFolders(folders.filter((folder) => folder.id !== folderId));
  };

  const handleCopy = async (msgIdx: number, msgContent: string) => {
    const parser = new DOMParser();
    const doc = parser.parseFromString(msgContent, "text/html");
    const plainText = doc.body.textContent || msgContent;

    try {
      await navigator.clipboard.writeText(plainText);
      setCopiedMessageId(msgIdx); // Now correctly typed

      // Reset after 2 seconds
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (err) {
      console.error("Copy failed: ", err);
      alert("Failed to copy text.");
    }
  };

  const [copiedMessageId, setCopiedMessageId] = useState<number | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [qgptSettings, setQGPTSettings] = useState({
    llmModel: "gpt-4",
    embeddingModel: "text-embedding-ada-002",
    temperature: 0.7,
    size: "2048", // Fix QGPTSettings type: ensure qgptSettings.size is a string, not a number
  });
  // Handler for saving settings
  const updateConfig = (settings: typeof qgptSettings) => {
    setQGPTSettings(settings);
    setShowSettings(false);
  };

  useEffect(() => {
    if (!email) {
      navigate("/");
    }
  }, [email, navigate]);

  useEffect(() => {
    if (currentChatId !== null) {
      // Only load if a chat is selected
      const cached = loadCachedMessages(`${currentChatId}`); // Use only chatId as key
      if (cached && cached.length > 0) {
        const withCacheFlag = cached.map((m: any) => ({
          ...m,
          isCached: true,
        }));
        setMessages(withCacheFlag);
      } else {
        setMessages([]); // Reset messages if no cached messages exist
      }
    } else {
      setMessages([]); // Ensure no messages are loaded when no chat is selected
    }
  }, [setMessages, currentChatId]); // Remove mode from dependencies

  useEffect(() => {
    if (currentChatId !== null) {
      // Save messages for the currently selected chat using a chatId-specific key.
      saveCachedMessages(messages, `${currentChatId}`);
    }
  }, [messages, currentChatId]); // Remove mode from dependencies

  useEffect(() => {
    const container = responseBoxRef.current;
    if (!container) return;

    const handleScroll = () => {
      const scrollTop = container.scrollTop;
      const scrollHeight = container.scrollHeight;
      const clientHeight = container.clientHeight;

      // Check if the user is at the bottom
      setShowScrollButton(scrollTop + clientHeight < scrollHeight - 250);
    };

    container.addEventListener("scroll", handleScroll);
    return () => {
      container.removeEventListener("scroll", handleScroll);
    };
  }, [messages, mode, currentChatId]);

  // Scroll to the bottom of .responseText container
  const scrollToBottom = () => {
    if (responseBoxRef.current) {
      responseBoxRef.current.scrollTop = responseBoxRef.current.scrollHeight;
      setShowScrollButton(false);
    }
  };

  // Auto-scroll whenever messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (!currentChatId) return; // No chat selected
    // Get the stored chatData for the current mode
    const stored = localStorage.getItem(`chatData_${mode}`);
    if (!stored) return;
    const chatData = JSON.parse(stored);
    let updated = false;

    // Update ungroupedChats if current chat is there
    chatData.ungroupedChats = chatData.ungroupedChats.map((chat: any) => {
      if (chat.id === currentChatId) {
        updated = true;
        return { ...chat, messages }; // update the messages
      }
      return chat;
    });

    // If not found in ungroupedChats, update in folders
    if (!updated) {
      chatData.folders = chatData.folders.map((folder: any) => {
        return {
          ...folder,
          chats: folder.chats.map((chat: any) => {
            if (chat.id === currentChatId) {
              updated = true;
              return { ...chat, messages };
            }
            return chat;
          }),
        };
      });
    }

    // Save back to localStorage
    localStorage.setItem(`chatData_${mode}`, JSON.stringify(chatData));
  }, [messages, currentChatId, mode]);

  const handleToggleSelectAll = () => {
    if (selectedFiles.length === files.length) {
      handleDeselectFile();
    } else {
      setSelectedFiles(files.map((file) => file.doc_id));
    }
  };

  const handleEmailClick = () => {
    setShowLogout(!showLogout);
  };

  const handleLogout = () => {
    setShowLogout(false);
    navigate("/");
  };

  // Patch: When Maps modal is opened, set mode to 'Maps'
  const handleOpenMapsModal = () => {
    setShowMapsModal(true);
    if (mode !== "Maps") setMode("Maps");
  };

  // Patch: When a new chat is created or selected, reset mode to default
  const handleSelectChat = (chat: any) => {
    setCurrentChatId(chat ? chat.id : null);
    if (mode !== defaultMode) setMode(defaultMode);
  };

  // Mic implementation function i.e speech to text

  // Speech-to-text state and functionality
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(
    null
  );

  // Initialize speech recognition
  useEffect(() => {
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
      const SpeechRecognition =
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();

      recognitionInstance.continuous = true;
      recognitionInstance.interimResults = true;
      recognitionInstance.lang = "en-US";

      recognitionInstance.onresult = (event: any) => {
        let finalTranscript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          }
        }
        if (finalTranscript) {
          setInput((prev) => prev + finalTranscript);
        }
      };

      recognitionInstance.onerror = (event: any) => {
        console.error("Speech recognition error:", event.error);
        setIsListening(false);
      };

      recognitionInstance.onend = () => {
        setIsListening(false);
      };

      setRecognition(recognitionInstance);
    }
  }, [setInput]);

  const toggleListening = () => {
    if (!recognition) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }

    if (isListening) {
      recognition.stop();
      setIsListening(false);
    } else {
      recognition.start();
      setIsListening(true);
    }
  };

  // Additional state for Maps integration
  const [showMapsModal, setShowMapsModal] = useState(false);
  const [mapsLoading, setMapsLoading] = useState(false);
  const [mapsData, setMapsData] = useState(null);

  // Handle Maps analysis results
  const handleLocationAnalyzed = useCallback(
    (analysisData) => {
      setMapsData(analysisData);

      if (!analysisData || !analysisData.analysis) {
        console.error("No analysis data available");
        return;
      }

      // Format the analysis for sending to the chat
      const placesCount = analysisData.places.length;
      const summary = analysisData.summary;

      // Create a message to display the location analysis
      let message = `### Location Analysis Results\n\n`;
      message += analysisData.analysis;

      message += `\n\n---\n\n`;
      message += `*Analysis based on ${placesCount} places found within ${summary.place_count}m radius. `;
      message += `Average rating: ${summary.average_rating.toFixed(1)}/5.0*`;

      // Add this message as an assistant message directly to the conversation
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: message,
          isCached: false,
        },
      ]);

      // Close the modal
      setShowMapsModal(false);
    },
    [setMessages]
  );

  // Maps Modal component
  const MapsModal = () => {
    const [mapError, setMapError] = useState(null);

    return (
      <div
        className={`modal ${showMapsModal ? "show" : ""}`}
        style={{ display: showMapsModal ? "block" : "none" }}
      >
        <div className="modal-dialog modal-lg">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title">Location Analysis with AI</h5>
              <button
                type="button"
                className="btn-close"
                onClick={() => setShowMapsModal(false)}
                aria-label="Close"
              ></button>
            </div>
            <div className="modal-body">
              {mapError ? (
                <div className="alert alert-danger">{mapError}</div>
              ) : (
                <MapsComponent
                  onLocationAnalyzed={handleLocationAnalyzed}
                  isLoading={mapsLoading}
                  setLoading={setMapsLoading}
                />
              )}
              <div className="text-muted mt-2">
                <small>
                  Select a location on the map and click "Analyze This Location"
                  to get AI-powered analysis of the area.
                </small>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="chat-container">
      <Navbar
        bg="white"
        variant="light"
        expand="lg"
        className="sticky-top shadow-sm border-bottom"
      >
        <Container fluid>
          <Navbar.Brand href="#home" className="mr-auto">
            <img src={Fiseclogo} alt="Fisec QGPT" style={{ height: "50px" }} />
          </Navbar.Brand>
          <Nav className="ml-auto">
            <Nav.Link href="#" className="text-dark" onClick={handleEmailClick}>
              {email}
              <span className="email-logo-wrapper">
                <EmailLogo email={email} />
              </span>
            </Nav.Link>
            <Button
              variant="danger"
              onClick={handleLogout}
              className="ml-3 btn-logout"
            >
              Logout
            </Button>
          </Nav>
        </Container>
      </Navbar>

      <div className="main-container">
        {/* Left Panel */}
        <div
          className={`left-panel ${sidebarLeftHidden ? "hidden" : ""}`}
          id="left-panel"
        >
          <div className="chat-mode">
            <div className="heading">
              <label>
                <strong>Chat Mode</strong>
              </label>
            </div>
            <select
              id="dropdown-mode"
              name="mode"
              value={mode}
              onChange={(e) => handleModeChange(e.target.value)}
              disabled={messageLoading}
            >
              <option value="RAG">RAG Mode</option>
              <option value="Basic">Basic Chat</option>
              <option value="Search">Search Mode</option>
              <option value="Summarize">Summarize</option>
              <option value="AgenticBot">Agentic Bot</option>
              <option value="ToolCalling">Tool Calling</option>
              <option value="Maps">Maps</option>
            </select>
          </div>{" "}
          <div className="file-upload">
            <div className="mode-description">
              {mode === "RAG" &&
                "RAG Mode: Extracts relevant document excerpts and incorporates them into the response."}
              {mode === "Search" &&
                "Search Mode: Scans documents to identify the most relevant content."}
              {mode === "Basic" &&
                "Basic Chat: Engages in a simple conversation without referencing additional documents."}
              {mode === "Summarize" &&
                "Summarize Mode: Generates a concise summary of your conversation."}
              {mode === "AgenticBot" &&
                "Agentic Bot: Acts autonomously, making decisions and taking actions to achieve goals."}
              {mode === "ToolCalling" &&
                "Tool Calling: Interact with external tools or APIs, deciding when and how to use them."}
            </div>
            <input
              id="file-upload-input"
              type="file"
              ref={fileInputRef}
              style={{ display: "none" }}
              onChange={onFileChange}
            />
            <div className="upload-section">
              <button
                className="btn secondary upload-files"
                onClick={() => fileInputRef.current?.click()}
              >
                Upload Files
              </button>

              {/* Cloud Storage Integration */}
              <div className="cloud-storage-section">
                <div className="cloud-storage-title">
                  <strong>Cloud Storage</strong>
                </div>
                <div className="cloud-storage-buttons">
                  <button
                    className="btn cloud-btn gdrive-btn"
                    onClick={handleConnectGoogleDrive}
                    disabled={fileLoading}
                    title="Import from Google Drive"
                  >
                    <img
                      src={GdriveImg}
                      alt="Google Drive"
                      style={{ width: "20px", height: "20px" }}
                    />
                    Google Drive
                  </button>
                  <button
                    className="btn cloud-btn onedrive-btn"
                    onClick={handleConnectOneDrive}
                    disabled={fileLoading}
                    title="Import from OneDrive"
                  >
                    <img
                      src={OneDriveImg}
                      alt="OneDrive"
                      style={{ width: "20px", height: "20px" }}
                    />
                    OneDrive
                  </button>
                  <button
                    className="btn cloud-btn maps-btn"
                    onClick={handleOpenMapsModal}
                    title="Analyze Location with Google Maps"
                  >
                    <FiMap
                      style={{
                        width: "20px",
                        height: "20px",
                        marginRight: "5px",
                      }}
                    />
                    Maps
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div className="ingested-files">
            <div className="d-flex justify-content-between align-items-center">
              <strong>Ingested Files</strong>
              <div className="d-flex align-items-center">
                <button
                  className="btn btn-link p-0"
                  onClick={handleToggleSelectAll}
                  disabled={files.length === 0}
                  title={
                    selectedFiles.length === files.length
                      ? "Deselect All"
                      : "Select All"
                  }
                >
                  {selectedFiles.length === files.length ? (
                    <FiCheckSquare size={16} style={{ color: "black" }} />
                  ) : (
                    <FiSquare size={16} style={{ color: "black" }} />
                  )}
                </button>
                <button
                  className="btn btn-link p-0 ml-2"
                  onClick={handleDeleteSelectedFiles}
                  disabled={selectedFiles.length === 0}
                  title="Delete Selected File(s)"
                >
                  <FiTrash2
                    size={16}
                    style={{ color: "red", marginLeft: "14px" }}
                  />
                </button>
              </div>
            </div>
            {fileLoading ? (
              <div className="spinner-container">
                <span className="spinner">
                  <br />
                </span>
              </div>
            ) : files.length > 0 ? (
              <ul className="files-listed">
                {files.map((file, idx) => (
                  <li
                    key={idx}
                    className="file-item d-flex align-items-center justify-content-between"
                  >
                    <div className="d-flex align-items-center">
                      <input
                        type="checkbox"
                        style={{ transform: "scale(1.5)", marginRight: "10px" }}
                        checked={selectedFiles.includes(file.doc_id)}
                        onChange={() => toggleFileSelection(file.doc_id)}
                      />
                      <span className="files-listed" style={{ color: "black" }}>
                        {file.file_name}
                      </span>
                    </div>
                    <button
                      className="btn btn-link p-0"
                      onClick={() => handleDeleteFile(file.doc_id)}
                      title="Delete this file"
                    >
                      <FiTrash2 size={16} style={{ color: "red" }} />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No files uploaded.</p>
            )}

            <div>
              <strong>Files selected for query or deletion</strong>
              <ul className="files-listed">
                {files.length === 0 ? (
                  <li>No files uploaded.</li>
                ) : selectedFiles.length > 0 ? (
                  files
                    .filter((file) => selectedFiles.includes(file.doc_id))
                    .map((file, idx) => <li key={idx}>{file.file_name}</li>)
                ) : (
                  <li>All files</li>
                )}
              </ul>
            </div>
          </div>
          {/* Render the ChatSidebar */}
          <ChatSidebar
            mode={mode}
            currentChatId={currentChatId}
            onSelectChat={handleSelectChat}
          />
        </div>

        {/* Center Panel */}
        <div
          id="center-panel"
          className={`center-panel ${
            !sidebarLeftHidden && !sidebarRightHidden
              ? "full-width"
              : !sidebarLeftHidden || !sidebarRightHidden
              ? "expended"
              : ""
          }`}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              width: "100%",
            }}
          >
            <div style={{ textAlign: "left" }}>
              <button
                id="sidebarLeft-toggle"
                className="toggle-btn"
                onClick={toggleSidebarLeft}
              >
                {sidebarLeftHidden ? (
                  <FiArrowRight size={16} />
                ) : (
                  <FiArrowLeft size={16} />
                )}
              </button>
            </div>
            <div style={{ textAlign: "right" }}>
              <button
                id="sidebarRight-toggle"
                className="toggle-btn"
                onClick={toggleSidebarRight}
              >
                {sidebarRightHidden ? (
                  <FiArrowLeft size={16} />
                ) : (
                  <FiArrowRight size={16} />
                )}
              </button>
            </div>
          </div>
          <div
            className="logo"
            style={{ display: "flex", alignItems: "center", gap: "1rem" }}
          >
            <span title="LLM Model">
              <FiMonitor style={{ marginRight: "4px" }} /> :{" "}
              {qgptSettings.llmModel}
            </span>{" "}
            |
            <span title="Embedding Model">
              <FiMonitor style={{ marginRight: "4px" }} /> :{" "}
              {qgptSettings.embeddingModel}
            </span>{" "}
            |
            <span title="Set Temperature">
              <FiThermometer style={{ marginRight: "4px" }} /> :{" "}
              {qgptSettings.temperature}
            </span>{" "}
            |
            <span title="Response size">
              <FiMaximize style={{ marginRight: "4px" }} /> :{" "}
              {qgptSettings.size}
            </span>
            <button
              title="QGPT Settings"
              className="btn secondary settings-btn"
              onClick={() => setShowSettings(true)}
            >
              <FiSettings size={18} />
            </button>
          </div>
          <div className="chat-box">
            {messages.length === 0 ? (
              <div className="hi-text" id="hiText">
                {currentChatId !== null
                  ? "How can I help you today?"
                  : "Select a chat or create one first"}
              </div>
            ) : (
              <div
                className="responseText"
                ref={responseBoxRef}
                style={{ whiteSpace: "pre-wrap", padding: "10px" }}
              >
                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`message ${
                      msg.role === "user" ? "user-message" : "bot-message"
                    }`}
                  >
                    {msg.role !== "user" && <span className="bot-icon" />}
                    <div className="message-container">
                      <div className="message-content">
                        {msg.role === "user" ? (
                          <ReactShowdown markdown={msg.content} />
                        ) : (
                          <div className="assistant-message-container">
                            {msg.isCached ? (
                              <ReactShowdown markdown={msg.content} />
                            ) : (
                              <StreamedResponse
                                fullResponse={msg.content}
                                speed={5}
                              />
                            )}
                            <button
                              className="copy-btn-assistant"
                              onClick={() => handleCopy(idx, msg.content)}
                              title="Copy assistant message"
                            >
                              {copiedMessageId === idx ? (
                                <FiCheck size={16} color="green" />
                              ) : (
                                <FiCopy size={16} />
                              )}
                            </button>
                          </div>
                        )}
                      </div>
                      {msg.role === "user" && (
                        <span className="user-logo-wrapper">
                          <EmailLogo email={email} className="user-logo" />
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {messages.length > 0 && showScrollButton && (
              <button className="scroll-to-bottom-btn" onClick={scrollToBottom}>
                <FiArrowDownCircle size={16} />
              </button>
            )}
            {/* Chat Input Section */}{" "}
            <div className="chat-query-input">
              {/* Hidden file input for regular file uploads */}
              <input
                type="file"
                style={{ display: "none" }}
                ref={fileInputRef}
                onChange={onFileChange}
              />
              {/* Hidden file input for image uploads */}
              <input
                type="file"
                accept="image/*"
                style={{ display: "none" }}
                ref={imageInputRef}
                onChange={onFileChange}
              />
              <div className="input-container">
                <textarea
                  id="chatInput"
                  placeholder="Type a message..."
                  rows={1}
                  value={input}
                  disabled={!currentChatId}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  style={{
                    overflowY: "scroll",
                    height: "80px",
                    scrollbarWidth: "none",
                  }}
                ></textarea>{" "}
                {/* Image Upload Button */}
                <button
                  className="image-upload-btn"
                  title="Upload Image"
                  onClick={() => imageInputRef.current?.click()}
                  type="button"
                >
                  <FiImage size={18} />
                </button>
                {/* Mic Button for Speech-to-Text */}
                <button
                  className="mic-btn"
                  title="Start voice input"
                  onClick={toggleListening}
                >
                  {isListening ? <FiMicOff size={18} /> : <FiMic size={18} />}
                </button>
                <button
                  className="chat-send-btn"
                  onClick={() =>
                    messageLoading ? handleStopMessage() : handleSendMessage()
                  }
                >
                  {messageLoading ? "■" : "↑"}
                </button>
              </div>
              <div className="buttons primary">
                {" "}
                <button
                  className="btn primary retry"
                  onClick={handleRetry}
                  disabled={messageLoading}
                >
                  Retry
                </button>{" "}
                <button
                  className="btn primary"
                  onClick={handleUndo}
                  disabled={messageLoading}
                >
                  Undo
                </button>
                <button
                  className="btn primary clear"
                  onClick={handleClearChat}
                  disabled={messageLoading}
                >
                  Clear
                </button>
              </div>
              <div className="input-container">
                <div className="expandable-wrapper">
                  <button
                    className="expandable-btn"
                    onClick={() => setShowInstructions(!showInstructions)}
                  >
                    {showInstructions
                      ? "▼ Hide Additional Instructions"
                      : "▶ Show Additional Instructions"}
                  </button>
                  {showInstructions && (
                    <AdditionalInstructions
                      systemPromptInput={systemPromptInput}
                      setSystemPromptInput={setSystemPromptInput}
                      prompts={totalPrompts}
                    />
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
        {/* Right Panel */}
        <div
          className={`right-panel ${sidebarRightHidden ? "hidden" : ""}`}
          id="right-panel"
        >
          <PromptPanel
            prompts={prompts}
            folders={folders}
            totalPrompts={totalPrompts}
            setTotalPrompts={setTotalPrompts} // Added this
            addFolder={addFolder}
            addPrompt={addPrompt}
            addPromptToFolder={addPromptToFolder}
            updatePrompt={updatePrompt}
            updateFolder={updateFolder}
            deletePrompt={deletePrompt}
            deleteFolder={deleteFolder}
          />
        </div>
      </div>

      <div className="footer">
        <div className="footer-everi-logo">
          {/* <img
            src={Picture1}
            alt="PrivateGPT"
            style={{ height: "70px", marginRight: "15px" }}
          /> */}
          <p className="footer-logo-text">
            QDL <br />
            QDL Core Services
            <br />
          </p>
        </div>
        <a className="footer-zylon-link" href="https://www.fisecglobal.net">
          Made at QuantumData Leap
        </a>
      </div>

      {/* QGPT Settings Modal */}
      <QGPTSettingsModal
        show={showSettings}
        onHide={() => setShowSettings(false)}
        onSave={updateConfig}
        initialSettings={qgptSettings}
      />

      {/* Maps Modal */}
      {showMapsModal && <MapsModal />}

      {/* Overlay for settings modal */}
      {showSettings && <div className="overlay"></div>}

      {/* Overlay for maps modal */}
      {showMapsModal && <div className="overlay"></div>}
    </div>
  );
};

export default Chat;
