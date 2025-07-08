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
  FiImage,
  FiEdit,
  FiPlus,
} from "react-icons/fi";
import { FaMapMarkedAlt } from "react-icons/fa"; // Add FaMapMarkedAlt  for maps feature
import EmailLogo from "./EmailLogo.tsx";
import PromptPanel from "./PromptPanel.tsx";
import AdditionalInstructions from "./AdditionalInstructions.tsx";
import MapsComponent from "./MapsComponent.tsx";
import GdriveImg from "./assets/gdrive.png";
import OneDriveImg from "./assets/one-drive.png";
import Fiseclogo from "./Fisec_QGPT_Logo.png";
import { extractCoordinatesFromText } from "./utils/coordinateUtils";
import {
  analyzeLocation,
  analyzeQuery,
  ollamaClassifyQuery,
  analyzeMapsQuery,
} from "./api.ts";
import axios from "axios";

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

// Type definitions for chats and folders
type Chat = {
  id: number;
  name: string;
  messages: any[];
};

type Folder = {
  id: number;
  name: string;
  chats: Chat[];
};

type ChatData = {
  folders: Folder[];
  ungroupedChats: Chat[];
};

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
  if (
    window &&
    (window as any).qgptSettings &&
    (window as any).qgptSettings.default_mode
  ) {
    defaultMode = (window as any).qgptSettings.default_mode;
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
  // Initialize with collapsed additional instructions
  const [showInstructions, setShowInstructions] = useState(false);
  const [selectedTone, setSelectedTone] = useState("");
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

  const addPrompt = (newPrompt: any) => {
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

  const addPromptToFolder = (folderId: number, newPrompt: any) => {
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
  const updatePrompt = (updatedPrompt: any) => {
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

  // New chat handling functions
  const getUniqueChatName = useCallback((): string => {
    const baseName = "Untitled";
    const stored = localStorage.getItem(`chatData_${mode}`);
    if (!stored) return baseName;

    const chatData: ChatData = JSON.parse(stored);
    const allChats = [
      ...chatData.ungroupedChats,
      ...chatData.folders.flatMap((folder) => folder.chats),
    ];

    const existingNames = new Set(allChats.map((chat) => chat.name));

    if (!existingNames.has(baseName)) {
      return baseName;
    }

    let count = 2;
    while (existingNames.has(`${baseName}(${count})`)) {
      count++;
    }

    return `${baseName}(${count})`;
  }, [mode]);

  const handleNewChat = useCallback(() => {
    return new Promise<number>((resolve) => {
      const newChat: Chat = {
        id: Date.now(),
        name: getUniqueChatName(),
        messages: [],
      };

      // Get current chat data for this mode
      const stored = localStorage.getItem(`chatData_${mode}`);
      const chatData: ChatData = stored
        ? JSON.parse(stored)
        : { folders: [], ungroupedChats: [] };

      // Add new chat to ungrouped chats
      chatData.ungroupedChats = [newChat, ...chatData.ungroupedChats];

      // Save back to localStorage
      localStorage.setItem(`chatData_${mode}`, JSON.stringify(chatData));

      // Select the new chat
      setCurrentChatId(newChat.id);
      setMessages([]);

      // Resolve with the new chat ID
      resolve(newChat.id);
    });
  }, [getUniqueChatName, mode, setCurrentChatId, setMessages]);

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
        console.log("[QGPT-UI] [DEBUG] Loaded messages from localStorage", {
          currentChatId,
          loaded: withCacheFlag,
        });
      } else {
        setMessages([]);
        console.log("[QGPT-UI] [DEBUG] No cached messages, setMessages([])", {
          currentChatId,
        });
      }
    } else {
      setMessages([]);
      console.log("[QGPT-UI] [DEBUG] No chat selected, setMessages([])");
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
    // Log whenever messages state changes
    console.log("[QGPT-UI] [DEBUG] messages state changed", { messages });
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

  // State to store coordinates for modal opening
  const [pendingMapCoords, setPendingMapCoords] = useState<{
    lat: number;
    lng: number;
  } | null>(null);

  // State to store coordinates for modal display
  const [mapCoordsForModal, setMapCoordsForModal] = useState<{
    lat: number;
    lng: number;
  } | null>(null);

  // Effect to open modal and set coordinates when pendingMapCoords is set
  useEffect(() => {
    if (pendingMapCoords) {
      setMapCoordsForModal(pendingMapCoords); // Store for modal
      setShowMapsModal(true);
      setPendingMapCoords(null); // Reset trigger
    }
  }, [pendingMapCoords]);

  // Handle Maps analysis results
  const handleLocationAnalyzed = useCallback(
    (analysisData: any) => {
      if (!analysisData || !analysisData.analysis) {
        console.error("No analysis data available");
        return;
      }

      // Extract nearest transit locations if available (flat list)
      const transitLocations = analysisData.nearest_transit || [];
      const center = analysisData.center || mapCoordsForModal || {};
      // Format the analysis for sending to the chat
      const placesCount = analysisData.places.length;
      const summary = analysisData.summary;

      // Create a message to display the location analysis
      let message = `### Location Analysis Results\n\n`;
      message += analysisData.analysis;

      // Add links to Google Maps for each transit location (flat list)
      if (transitLocations.length > 0 && center.lat && center.lng) {
        message += `\n\n**Nearest Transit Locations:**\n`;
        transitLocations.forEach((loc: any) => {
          const gmapsUrl = `https://www.google.com/maps/dir/?api=1&origin=${center.lat},${center.lng}&destination=${loc.lat},${loc.lng}`;
          let dist = loc.distance_km ? `${loc.distance_km.toFixed(1)} km` : "N/A";
          let duration = loc.duration_text ? `, ${loc.duration_text}` : "";
          message += `- ${loc.type ? loc.type.charAt(0).toUpperCase() + loc.type.slice(1) : loc.name}: <a href="${gmapsUrl}" target="_blank">Directions</a> (${dist}${duration})\n`;
        });
      }

      // Add a direct 'Open on Maps' link for the center
      if (center.lat && center.lng) {
        message += `\n[Open on Maps](https://www.google.com/maps/search/?api=1&query=${center.lat},${center.lng})\n`;
      }

      message += `\n\n---\n\n`;
      message += `*Analysis based on ${placesCount} places found within ${summary.place_count}m radius. `;
      message += `Average rating: ${summary.average_rating?.toFixed(1) || "N/A"}/5.0*`;

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: message,
          isCached: false,
        },
      ]);
      setShowMapsModal(false);
    },
    [setMessages, mapCoordsForModal]
  );

  // Maps Modal component
  const MapsModal = () => {
    // Pass transit locations to MapsComponent for marker rendering
    const transitLocations =
      (typeof mapsData !== "undefined" &&
        mapsData &&
        mapsData.nearest_transit) ||
      [];
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
                onClick={() => {
                  setShowMapsModal(false);
                  setMapCoordsForModal(null);
                }}
                aria-label="Close"
              ></button>
            </div>
            <div className="modal-body">
              <MapsComponent
                onLocationAnalyzed={handleLocationAnalyzed}
                isLoading={mapsLoading}
                setLoading={setMapsLoading}
                centerCoords={mapCoordsForModal}
                transitLocations={transitLocations}
              />
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

  // Enhanced: Use Ollama to intelligently route queries
  const handleSendMessageWithMaps = async () => {
    console.log("[QGPT-UI] [DEBUG] handleSendMessageWithMaps CALLED", {
      input,
      messageLoading,
      currentChatId,
      messages,
    });
    if (!input.trim() || messageLoading) return;

    // Store the user input to display immediately
    const userInput = input.trim();

    // --- COORDINATE-ONLY DETECTION: force Maps mode if coordinates detected ---
    let coords = extractCoordinatesFromText(userInput);
    if (!coords) {
      // Matches: 17.385044, 78.486671 or 17.385044 78.486671 (with optional whitespace)
      const coordRegex = /([-+]?\d{1,2}\.\d+)[,\s]+([-+]?\d{1,3}\.\d+)/;
      const match = userInput.match(coordRegex);
      if (match) {
        coords = { lat: parseFloat(match[1]), lng: parseFloat(match[2]) };
      }
    }
    if (coords) {
      setMode("Maps");
      setMessages((prev) => [
        ...prev,
        { role: "user", content: userInput, isCached: false },
        { role: "assistant", content: '<div className="spinner2"></div>', isCached: false },
      ]);
      setInput("");
      setTimeout(async () => {
        const result = await analyzeLocation(coords.lat, coords.lng);
        let message = (result.analysis || "No analysis available.") +
          `<br/><a href="https://www.google.com/maps/search/?api=1&query=${coords.lat},${coords.lng}" target="_blank" rel="noopener noreferrer">Open on Maps</a>`;
        if (result.nearest_transit && Array.isArray(result.nearest_transit)) {
          message += `<br/><b>Nearest Transit Locations:</b><ul>`;
          result.nearest_transit.forEach((loc: any) => {
            const gmapsUrl = `https://www.google.com/maps/dir/?api=1&origin=${coords.lat},${coords.lng}&destination=${loc.lat},${loc.lng}`;
            let dist = loc.distance_km ? `${loc.distance_km.toFixed(1)} km` : "N/A";
            let duration = loc.duration_text ? `, ${loc.duration_text}` : "";
            message += `<li>${loc.type ? loc.type.charAt(0).toUpperCase() + loc.type.slice(1) : loc.name}: <a href="${gmapsUrl}" target="_blank">Directions</a> (${dist}${duration})</li>`;
          });
          message += `</ul>`;
        }
        setMessages((prev) => {
          const newMsgs = [...prev];
          newMsgs[newMsgs.length - 1] = {
            role: "assistant",
            content: message,
            isCached: false,
          };
          return newMsgs;
        });
      }, 10);
      return;
    }
    // --- END COORDINATE-ONLY DETECTION ---

    // Now check for locationMatch only if coords not found
    const locationMatch = userInput.match(/location\s+([\w\s,.'-]+)/i);
    if (locationMatch) {
      const locationName = locationMatch[1].trim();
      const apiKey =
        process.env.REACT_APP_GOOGLE_MAPS_API_KEY ||
        "AIzaSyCcxJN30ArOo4yHON6oxSkthLXtT4B_p2o";
      const geocodeUrl = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(
        locationName
      )}&key=${apiKey}`;
      const geoResp = await axios.get(geocodeUrl);
      const geoData = geoResp.data;
      if (
        geoData.status === "OK" &&
        geoData.results &&
        geoData.results[0]
      ) {
        const { lat, lng } = geoData.results[0].geometry.location;
        const mapsInfo = geoData.results[0];
        try {
          const result = await analyzeLocation(
            lat,
            lng,
            1000,
            [],
            undefined,
            mapsInfo
          );
          const message =
            (result.analysis || "No analysis available.") +
            `<br/><a href="#" class="open-on-maps-link" data-lat="${lat}" data-lng="${lng}">Open on Maps</a>`;
          setMessages((prev) => {
            const newMsgs = [...prev];
            newMsgs[newMsgs.length - 1] = {
              role: "assistant",
              content: message,
              isCached: false,
            };
            console.log(
              "[QGPT-UI] [AssistantMsg] setMessages called (geocode)",
              { newMsgs }
            );
            return newMsgs;
          });
        } catch (err) {
          setMessages((prev) => {
            const newMsgs = [...prev];
            newMsgs[newMsgs.length - 1] = {
              role: "assistant",
              content: "Error analyzing location with LLM.",
              isCached: false,
            };
            console.log(
              "[QGPT-UI] [AssistantMsg] setMessages called (geocode error)",
              { newMsgs }
            );
            return newMsgs;
          });
        }
        return;
      } else {
        setMessages((prev) => {
          const newMsgs = [...prev];
          newMsgs[newMsgs.length - 1] = {
            role: "assistant",
            content: `Could not find location: ${locationName}`,
            isCached: false,
          };
          console.log(
            "[QGPT-UI] [AssistantMsg] setMessages called (location not found)",
            { newMsgs }
          );
          return newMsgs;
        });
        return;
      }
    } else {
      try {
        const result = await analyzeMapsQuery(userInput);
        const message = result.analysis || "No analysis available.";
        setMessages((prev) => {
          const newMsgs = [...prev];
          newMsgs[newMsgs.length - 1] = {
            role: "assistant",
            content: message,
            isCached: false,
          };
          console.log(
            "[QGPT-UI] [AssistantMsg] setMessages called (maps query)",
            { newMsgs }
          );
          return newMsgs;
        });
      } catch (err) {
        setMessages((prev) => {
          const newMsgs = [...prev];
          newMsgs[newMsgs.length - 1] = {
            role: "assistant",
            content: "Error analyzing query for maps.",
            isCached: false,
          };
          console.log(
            "[QGPT-UI] [AssistantMsg] setMessages called (maps query error)",
            { newMsgs }
          );
          return newMsgs;
        });
      }
      return;
    }
  };

  return (
    <div className="chat-container">
      <Navbar
        bg="white"
        variant="light"
        expand="lg"
        className="sticky-top shadow-sm border-bottom"
        style={{ padding: 0 }}
      >
        <Container fluid>
          <Navbar.Brand href="#home" className="mr-auto">
            <img src={Fiseclogo} alt="Fisec QGPT" style={{ height: "30px" }} />
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
              style={{ height: "fit-content" }}
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
              <option value="RAG" className="dropdown-options">
                RAG Mode
              </option>
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
                    <FaMapMarkedAlt
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

        {/* Center Panel - Modern Layout */}
        <div
          id="center-panel"
          className={`center-panel ${
            !sidebarLeftHidden && !sidebarRightHidden
              ? "full-width"
              : !sidebarLeftHidden || !sidebarRightHidden
              ? "expanded"
              : ""
          }`}
        >
          {/* Modern Chat Header */}
          <div className="chat-header">
            <div className="chat-header-left">
              <button
                className="toggle-btn"
                onClick={toggleSidebarLeft}
                title="Toggle Left Panel"
              >
                {sidebarLeftHidden ? (
                  <FiArrowRight size={16} />
                ) : (
                  <FiArrowLeft size={16} />
                )}
              </button>
            </div>

            <div className="chat-header-center">
              <div className="settings-info">
                <span title="LLM Model">
                  <FiMonitor size={14} />
                  {qgptSettings.llmModel}
                </span>
                <span title="Response Size">
                  <FiMaximize size={14} />
                  {qgptSettings.size}
                </span>
              </div>
            </div>

            <div className="chat-header-right">
              <button
                className="settings-btn"
                onClick={() => setShowSettings(true)}
                title="Settings"
              >
                <FiSettings size={16} />
              </button>

              <button
                className="toggle-btn"
                onClick={toggleSidebarRight}
                title="Toggle Right Panel"
              >
                {sidebarRightHidden ? (
                  <FiArrowLeft size={16} />
                ) : (
                  <FiArrowRight size={16} />
                )}
              </button>
            </div>
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
            {/* Chat Input Section */}
            <div className="chat-query-input">
              {/* Compact Tone Analyzer */}
              {/* <div className="tone-selector-wrapper">
                <div className="tone-selector">
                  <label htmlFor="toneSelect" className="tone-label">
                    <FiEdit size={14} />
                    <span>Tone:</span>
                  </label>
                  <select
                    id="toneSelect"
                    value={selectedTone}
                    onChange={(e) => setSelectedTone(e.target.value)}
                    className="tone-dropdown"
                  >
                    <option value="">Default</option>
                    {totalPrompts.map((prompt, index) => (
                      <option key={index} value={prompt.content}>
                        {prompt.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div> */}

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
              <div className="chat-input-wrapper">
                <div className="chat-input-container">
                  <textarea
                    id="chatInput"
                    placeholder={
                      currentChatId
                        ? "Type a message..."
                        : "Type a message to start a new chat..."
                    }
                    rows={1}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        console.log("[QGPT-UI] [Input] Enter pressed", {
                          currentChatId,
                          input: input.trim(),
                          messageLoading,
                        });
                        if (input.trim() && !messageLoading) {
                          // If no chat is selected, create a new one first
                          if (!currentChatId) {
                            handleNewChat()
                              .then(() => {
                                // Use setTimeout to ensure state has updated
                                setTimeout(() => {
                                  console.log(
                                    "[QGPT-UI] [Input] handleSendMessageWithMaps after new chat"
                                  );
                                  handleSendMessageWithMaps().catch(
                                    console.error
                                  );
                                }, 50);
                              })
                              .catch(console.error);
                          } else {
                            console.log("[QGPT-UI] [Input] Sending message...");
                            handleSendMessageWithMaps().catch(console.error);
                          }
                        } else {
                          console.log(
                            "[QGPT-UI] [Input] Message not sent - conditions not met"
                          );
                        }
                      }
                    }}
                    className="chat-input-textarea"
                  ></textarea>
                  <div className="chat-input-buttons">
                    {/* Image Upload Button */}
                    <button
                      className="input-action-btn image-upload-btn"
                      title="Upload Image"
                      onClick={() => imageInputRef.current?.click()}
                      type="button"
                    >
                      <FiImage size={18} />
                    </button>
                    {/* Mic Button for Speech-to-Text */}
                    <button
                      className="input-action-btn mic-btn"
                      title="Start voice input"
                      onClick={toggleListening}
                    >
                      {isListening ? (
                        <FiMicOff size={18} />
                      ) : (
                        <FiMic size={18} />
                      )}
                    </button>
                    <button
                      className="input-action-btn chat-send-btn"
                      onClick={() => {
                        if (messageLoading) {
                          handleStopMessage();
                        } else if (input.trim()) {
                          // If no chat is selected, create a new one first
                          if (!currentChatId) {
                            handleNewChat()
                              .then(() => {
                                // Use setTimeout to ensure state has updated
                                setTimeout(() => {
                                  console.log(
                                    "[QGPT-UI] [SendBtn] handleSendMessageWithMaps after new chat"
                                  );
                                  handleSendMessageWithMaps().catch(
                                    console.error
                                  );
                                }, 50);
                              })
                              .catch(console.error);
                          } else {
                            console.log(
                              "[QGPT-UI] [SendBtn] Sending message..."
                            );
                            handleSendMessageWithMaps().catch(console.error);
                          }
                        }
                      }}
                    >
                      {messageLoading ? "■" : "↑"}
                    </button>
                  </div>
                </div>
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
        {/* Right Panel - Chat Management & Quick Actions */}
        <div
          className={`right-panel ${sidebarRightHidden ? "hidden" : ""}`}
          id="right-panel"
        >
          {/* Chat Actions Section */}
          <div className="section">
            <div className="d-flex align-items-center justify-content-between mb-3">
              <label className="mb-0">
                <strong>Chat Actions</strong>
              </label>
            </div>
            <div className="chat-actions-grid">
              <Button
                variant="outline-primary"
                size="sm"
                className="action-btn"
                onClick={() => handleNewChat().catch(console.error)}
                title="Start New Chat"
              >
                <FiPlus size={10} />
                <span>New</span>
              </Button>
              <Button
                variant="outline-secondary"
                size="sm"
                className="action-btn"
                onClick={handleClearChat}
                disabled={messageLoading}
                title="Clear Current Chat"
              >
                <FiTrash2 size={10} />
                <span>Clear</span>
              </Button>
              <Button
                variant="outline-info"
                size="sm"
                className="action-btn"
                onClick={handleRetry}
                disabled={messageLoading}
                title="Retry Last Message"
              >
                <FiArrowLeft size={10} />
                <span>Retry</span>
              </Button>
              <Button
                variant="outline-warning"
                size="sm"
                className="action-btn"
                onClick={handleUndo}
                disabled={messageLoading}
                title="Undo Last Message"
              >
                <FiArrowLeft size={10} />
                <span>Undo</span>
              </Button>
            </div>
          </div>

          {/* Temperature Control Section */}
          <div className="section">
            <div className="d-flex align-items-center justify-content-between mb-3">
              <label className="mb-0">
                <strong>Temperature Control</strong>
              </label>
            </div>
            <div className="temperature-control">
              <div className="d-flex align-items-center gap-2 mb-2">
                <FiThermometer size={12} />
                <span
                  className="temperature-label"
                  title={`Current temperature: ${qgptSettings.temperature}`}
                >
                  Temp: {qgptSettings.temperature}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={qgptSettings.temperature}
                onChange={(e) => {
                  const newTemp = parseFloat(e.target.value);
                  setQGPTSettings({ ...qgptSettings, temperature: newTemp });
                }}
                className="temperature-slider"
                title={`Temperature: ${qgptSettings.temperature}`}
              />
              <div className="d-flex justify-content-between text-muted small">
                <span>Conservative</span>
                <span>Creative</span>
              </div>
            </div>
          </div>

          {/* Tone Templates Section */}
          <PromptPanel
            prompts={prompts}
            folders={folders}
            totalPrompts={totalPrompts}
            setTotalPrompts={setTotalPrompts}
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
        <div className="footer-logo">
          <p className="footer-logo-text">Quantum Data Leap GPT</p>
        </div>
        <a className="footer-link" href="https://www.fisecglobal.net">
          Powered by Quantum Data Leap
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
    </div>
  );
};

export default Chat;
