import React, { useState, useEffect, useRef } from "react";
import { useChatHandlers } from "./api.ts";
import StreamedResponse from "./StreamedResponse.tsx";
import ReactShowdown from "react-showdown";
import "./style.css";
import { useLocation, useNavigate } from "react-router-dom";
import { Navbar, Container, Nav, Button } from "react-bootstrap";
import QGPTSettingsModal, { QGPTSettings } from "./popup.tsx";
import ChatSidebar from "./sidebar/ChatSidebar.tsx";
import { Modal, Input, Alert } from "antd";
import {
  FiCopy,
  FiArrowDownCircle,
  FiMenu,
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
} from "react-icons/fi";
import EmailLogo from "./EmailLogo.tsx";
import PromptPanel from "./PromptPanel.tsx";
import GdriveImg from "./assets/gdrive.png";
import OneDriveImg from "./assets/one-drive.png";
import AdditionalInstructions from "./AdditionalInstructions.tsx";

import Picture1 from "./Fisec_QGPT_Logo.png";
import icon from "./avatar-bot.ico";

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
  const {
    messages,
    input,
    setInput,
    mode,
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
    handleDeleteAllFiles,
    handleClearChat,
    onFileChange,
    toggleSidebarLeft,
    toggleSidebarRight,
    handleStopMessage,
    systemPromptInput,
    setSystemPromptInput,
    setMessages,
    setSelectedFiles,
    handleDeleteFile,
    API_URL,
    currentChatId,
    setCurrentChatId,
    refreshFiles,
  } = useChatHandlers();

  const [showLogout, setShowLogout] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const email = location.state?.email || localStorage.getItem("userEmail");
  const [showInstructions, setShowInstructions] = useState(true);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const responseBoxRef = useRef<HTMLDivElement>(null);
  const [isGDriveModalOpen, setIsGDriveModalOpen] = useState(false);
  const [gDriveApiKey, setGDriveApiKey] = useState("");
  const [gDriveClientId, setGDriveClientId] = useState("");
  const [credentialError, setCredentialError] = useState<string | null>(null);

  const handleSelectChat = (chat: { id: number; messages: any[] } | null) => {
    if (!chat) {
      setMessages([]); // Handle null case with an empty array or fallback
      setCurrentChatId(null); // Assuming null is a valid value for setCurrentChatId
      return;
    }
    // Attempt to load stored messages for the selected chat:
    const storedMessages = loadCachedMessages(`${mode}_${chat.id}`);
    if (storedMessages) {
      setMessages(storedMessages);
    } else {
      // If nothing is stored yet, use the chat’s default messages.
      setMessages(chat.messages);
    }
    setCurrentChatId(chat.id);
  };

  // QGPT Settings state
  const [qgptSettings, setQgptSettings] = useState<QGPTSettings>({
    llmModel: "",
    temperature: 1.0,
    size: "M",
    embeddingModel: "",
  });

  const [copiedMessageId, setCopiedMessageId] = useState<number | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  // Fetch initial config from the API on mount
  useEffect(() => {
    fetch(`${API_URL}/v1/config`)
      .then((res) => res.json())
      .then((data) => {
        setQgptSettings((prevSettings) => ({
          ...prevSettings,
          llmModel: data.llm_model,
          embeddingModel: data.embedding_model,
        }));
      })
      .catch((error) => console.error("Error fetching config:", error));
  }, []);

  // Function to update config via API and update local state/UI
  const updateConfig = async (newSettings: QGPTSettings) => {
    try {
      await fetch(`${API_URL}/v1/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          llmModel: newSettings.llmModel,
          embeddingModel: newSettings.embeddingModel,
        }),
      });
      setQgptSettings(newSettings);
      setShowSettings(false); // Close the modal after saving
    } catch (error) {
      console.error("Error updating config:", error);
    }
  };

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

  useEffect(() => {
    updateTotalPrompts();
  }, [folders, prompts]);

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

  // Update total prompts (to include paths)
  const updateTotalPrompts = () => {
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

  useEffect(() => {
    if (!email) {
      navigate("/");
    }
  }, [email, navigate]);

  useEffect(() => {
    if (currentChatId !== null) {
      // Only load if a chat is selected
      const cached = loadCachedMessages(`${mode}_${currentChatId}`);
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
  }, [setMessages, mode, currentChatId]);

  useEffect(() => {
    setCurrentChatId(null);
  }, [mode]);

  useEffect(() => {
    if (currentChatId !== null) {
      // Save messages for the currently selected chat using a mode-specific key.
      saveCachedMessages(messages, `${mode}_${currentChatId}`);
    }
  }, [messages, currentChatId, mode]);

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

  // Mic implementation function i.e speech to text

  const [isListening, setIsListening] = useState<boolean>(false);
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(
    null
  );

  useEffect(() => {
    // Check for speech recognition support
    if (
      !("webkitSpeechRecognition" in window || "SpeechRecognition" in window)
    ) {
      console.error("Speech recognition not supported in this browser");
      return;
    }

    // Define the SpeechRecognition type
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    const recognitionInstance = new SpeechRecognition();

    recognitionInstance.continuous = false; // Stop when user stops speaking
    recognitionInstance.interimResults = true; // Show real-time transcription
    recognitionInstance.lang = "en-US"; // Set language

    recognitionInstance.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0].transcript)
        .join("");

      setInput(transcript); // Update input without causing a loop
    };

    recognitionInstance.onend = () => {
      setIsListening(false);
      if (input.trim()) {
        handleSendMessage(input);
        setInput(""); // Clear input after sending
      }
    };

    recognitionInstance.onerror = (event: SpeechRecognitionErrorEvent) => {
      console.error("Speech recognition error:", event.error);
      setIsListening(false);
    };

    setRecognition(recognitionInstance);

    // Clean up the recognition instance on unmount
    return () => {
      recognitionInstance.abort();
    };
  }, []); // Run only once on mount

  const toggleListening = () => {
    if (!recognition) return;
    if (isListening) {
      recognition.stop();
      setIsListening(false);
    } else {
      setInput(""); // Clear input before new speech
      recognition.start();
      setIsListening(true);
    }
  };

  const checkGDriveCredentials = async (): Promise<boolean> => {
    try {
      // const response = await fetch(`${API_URL}/v1/drive/credentials`);
      // if (!response.ok) throw new Error("Failed to check credentials");
      // const data = await response.json();
      // return data.hasCredentials;
      return true;
    } catch (error) {
      console.error("Error checking GDrive credentials:", error);
      return false;
    }
  };

  const checkOneDriveCredentials = async (): Promise<boolean> => {
    try {
      // const response = await fetch(`${API_URL}/v1/drive/credentials`);
      // if (!response.ok) throw new Error("Failed to check credentials");
      // const data = await response.json();
      // return data.hasCredentials;
      return false;
    } catch (error) {
      console.error("Error checking GDrive credentials:", error);
      return false;
    }
  };

  const handleGDriveClick = async (): Promise<void> => {
    try {
      const hasCredentials = await checkGDriveCredentials();
      if (!hasCredentials) {
        // Show modal if credentials are missing
        setIsGDriveModalOpen(true);
        return;
      }
      const response = await fetch(`${API_URL}/v1/drive/injestfiles`);
      if (!response.ok) throw new Error("GDrive request failed");
      refreshFiles(); // Refresh files after successful request
    } catch (error) {
      console.error("Error triggering GDrive:", error);
    }
  };

  const handleGDriveModalSubmit = async (): Promise<void> => {
    if (!gDriveApiKey || !gDriveClientId) {
      setCredentialError("Please enter both API Key and Client ID.");
      return;
    }

    const success = await saveGDriveCredentials();
    if (success) {
      // Close modal, clear inputs, and proceed with ingestion
      setIsGDriveModalOpen(false);
      setGDriveApiKey("");
      setGDriveClientId("");
      setCredentialError(null);
      // Trigger file ingestion
      const response = await fetch(`${API_URL}/v1/drive/injestfiles`);
      if (!response.ok) throw new Error("GDrive request failed");
      await refreshFiles();
    }
  };

  const handleOneDriveClick = async (): Promise<void> => {
    try {
      const hasCredentials = await checkOneDriveCredentials();
      if (!hasCredentials) {
        // Show modal if credentials are missing
        setIsGDriveModalOpen(true);
        return;
      }
      const response = await fetch(`${API_URL}v1/onedrive/injestfiles`);
      if (!response.ok) throw new Error("OneDrive request failed");
      refreshFiles();
    } catch (error) {
      console.error("Error triggering OneDrive:", error);
    }
  };

  return (
    <div className="chat-container">
      <Modal
        title="Enter Drive Credentials"
        open={isGDriveModalOpen}
        onCancel={() => {
          setIsGDriveModalOpen(false);
          setGDriveApiKey("");
          setGDriveClientId("");
          setCredentialError(null);
        }}
        footer={[
          <Button
            key="cancel"
            onClick={() => {
              setIsGDriveModalOpen(false);
              setGDriveApiKey("");
              setGDriveClientId("");
              setCredentialError(null);
            }}
          >
            Cancel
          </Button>,
          <Button key="submit" type="primary" onClick={handleGDriveModalSubmit}>
            Save and Ingest
          </Button>,
        ]}
      >
        <div style={{ marginBottom: "16px" }}>
          <label htmlFor="gDriveApiKey">API Key</label>
          <Input
            id="gDriveApiKey"
            value={gDriveApiKey}
            onChange={(e) => setGDriveApiKey(e.target.value)}
            placeholder="Enter  Drive API Key"
          />
        </div>
        <div style={{ marginBottom: "16px" }}>
          <label htmlFor="gDriveClientId">Client ID</label>
          <Input
            id="gDriveClientId"
            value={gDriveClientId}
            onChange={(e) => setGDriveClientId(e.target.value)}
            placeholder="Enter  Drive Client ID"
          />
        </div>
        {credentialError && (
          <Alert message={credentialError} type="error" showIcon />
        )}
      </Modal>
      <Navbar
        bg="white"
        variant="light"
        expand="lg"
        className="sticky-top shadow-sm border-bottom"
      >
        <Container fluid>
          <Navbar.Brand href="#home" className="mr-auto">
            <img src={Picture1} alt="PrivateGPT" style={{ height: "70px" }} />
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
            </select>
          </div>

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
            <button
              className="btn secondary upload-files"
              onClick={() => fileInputRef.current?.click()}
            >
              Upload
            </button>
          </div>
          <div style={{ display: "flex", gap: "20px", alignItems: "center" }}>
            <div
              onClick={handleGDriveClick}
              style={{
                display: "flex",
                alignItems: "center",
                cursor: "pointer",
              }}
            >
              <img
                src={GdriveImg}
                alt="Google Drive"
                style={{ height: "30px", marginRight: "5px" }}
              />
            </div>
            <div
              onClick={handleOneDriveClick}
              style={{
                display: "flex",
                alignItems: "center",
                cursor: "pointer",
              }}
            >
              <img
                src={OneDriveImg}
                alt="One Drive"
                style={{ height: "30px", marginRight: "5px" }}
              />
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
                    {msg.role !== "user" && (
                      <img src={icon} alt="bot" className="bot-icon" />
                    )}
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
            {/* Chat Input Section */}
            <div className="chat-query-input">
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
                ></textarea>
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
                <button
                  className="btn primary retry"
                  onClick={handleRetry}
                  disabled={messageLoading}
                >
                  🔄 Retry
                </button>
                <button
                  className="btn primary"
                  onClick={handleUndo}
                  disabled={messageLoading}
                >
                  ↩️ Undo
                </button>
                <button
                  className="btn primary clear"
                  onClick={handleClearChat}
                  disabled={messageLoading}
                >
                  🗑️ Clear
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
          <img
            src={Picture1}
            alt="PrivateGPT"
            style={{ height: "70px", marginRight: "15px" }}
          />
          <p className="footer-logo-text">
            QDL <br />
            QDL Core Services
            <br />
          </p>
        </div>
        <a className="footer-zylon-link" href="https://www.fisecglobal.net">
          Made at QuantumData Leap
          <img className="footer-zylon-ico" src={icon} alt="Zylon" />
        </a>
      </div>

      {/* QGPT Settings Modal */}
      <QGPTSettingsModal
        show={showSettings}
        onHide={() => setShowSettings(false)}
        onSave={updateConfig}
        initialSettings={qgptSettings}
      />
    </div>
  );
};

export default Chat;
