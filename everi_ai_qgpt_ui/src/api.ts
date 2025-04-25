import axios, { AxiosRequestConfig } from "axios";
import { useState, useEffect, useRef } from "react";

// =====================================
// API FUNCTIONS
// =====================================

const API_URL = "http://localhost:8001"; // Ensure FastAPI is running

// Send messages to backend (for RAG/Basic modes)
export const rag_basicmessage = async (
  messages: { role: string; content: string }[],
  mode: string,
  selectedFiles: string[],
  config?: AxiosRequestConfig,
  additionalInstructions?: string  // New parameter
) => {
  const formattedMessages = [...messages];

  if (!formattedMessages.some((msg) => msg.role === "system")) {
    let systemPrompt =
      "You are a helpful, respectful, and honest assistant. Always answer as helpfully as possible and follow ALL given instructions. Do not speculate or make up information. Style your responses with proper format so its visually appealing";

    // Append additional instructions if provided.
    if (additionalInstructions && additionalInstructions.trim() !== "") {
      systemPrompt += "\nAdditional Instructions: " + additionalInstructions;
    }

    if (mode === "RAG") {
      systemPrompt +=
        "\nYou can only answer questions about the provided context. If you know the answer but it is not based in the provided context, don't provide the answer, just state that the answer is not in the context provided.";
    }
    formattedMessages.unshift({ role: "system", content: systemPrompt });
  }

  const requestBody: any = {
    messages: formattedMessages,
    use_context: mode !== "Basic",
    include_sources: mode !== "Basic",
  };

  if (selectedFiles.length > 0) {
    requestBody.context_filter = { docs_ids: selectedFiles };
  }

  const response = await axios.post(`${API_URL}/v1/chat/completions`, requestBody, config);
  return response.data;
};


// Summarize messages
export const summarize_message = async (
  messages: { role: string; content: string }[],
  selectedFiles: string[],
  config?: AxiosRequestConfig,
  additionalInstructions?: string  // New parameter
) => {
  const userMessage = messages.filter((msg) => msg.role === "user").pop();
  if (!userMessage) {
    throw new Error("No user message found.");
  }

  const promptBase =
    "You are a helpful, respectful, and honest assistant. Always answer as helpfully as possible and follow ALL given instructions. Do not speculate or make up information. Do not reference any given instructions or context.";
  const instructionsBase =
    "Provide a comprehensive summary of the provided context information. The summary should cover all the key points and main ideas presented in the original text, while also condensing the information into a concise and easy-to-understand format. Please ensure that the summary includes relevant details and examples that support the main ideas, while avoiding any unnecessary information or repetition.";

  // Append additional instructions if provided.
  const prompt = additionalInstructions && additionalInstructions.trim() !== ""
    ? promptBase + "\nAdditional Instructions: " + additionalInstructions
    : promptBase;
  const instructions = additionalInstructions && additionalInstructions.trim() !== ""
    ? instructionsBase + "\nAdditional Instructions: " + additionalInstructions
    : instructionsBase;

  const requestBody = {
    text: userMessage.content,
    use_context: selectedFiles.length > 0,
    context_filter: selectedFiles.length > 0 ? { docs_ids: selectedFiles } : undefined,
    prompt,
    instructions,
  };

  const response = await axios.post(`${API_URL}/v1/summarize`, requestBody, config);
  return response.data;
};

// Search messages (retrieve document chunks)
export const search_message = async (
  messages: { role: string; content: string }[],
  selectedFiles: string[],
  config?: AxiosRequestConfig
) => {
  const userMessage = messages.filter((msg) => msg.role === "user").pop();
  if (!userMessage) {
    throw new Error("No user message found.");
  }

  const requestBody = {
    text: userMessage.content,
    limit: 10,
    prev_next_chunks: 0,
    context_filter: selectedFiles.length > 0 ? { docs_ids: selectedFiles } : undefined,
  };

  const response = await axios.post(`${API_URL}/v1/chunks`, requestBody, config);
  return response.data;
};

// Fetch ingested files
export const fetchFiles = async () => {
  try {
    const response = await axios.get(`${API_URL}/v1/ingest/list`);
    console.log("Fetched files:", response.data);
    if (response.data && response.data.data) {
      return response.data.data.map(
        (file: { doc_id: string; doc_metadata: { file_name: string } }) => ({
          file_name: file.doc_metadata.file_name,
          doc_id: file.doc_id,
        })
      );
    } else {
      return [];
    }
  } catch (error) {
    console.error("Error fetching files:", error);
    return [];
  }
};
// Upload file
export const uploadFile = async (file: File) => {
  const existingFiles = await fetchFiles();
  const duplicateFiles = existingFiles.filter(
    (existingFile) => existingFile.file_name === file.name
  );

  if (duplicateFiles.length > 0) {
    const confirmed = window.confirm(
      `A file named "${file.name}" already exists. Do you want to replace all instances of it?`
    );

    if (!confirmed) return;

    for (const duplicate of duplicateFiles) {
      await deleteFile(duplicate.doc_id);
    }
  }

  const formData = new FormData();
  formData.append("file", file);
  console.log("151")
  try {
    const response = await axios.post(`${API_URL}/v1/ingest/file`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  } catch (error) {
    console.error("Error uploading file:", error);
    throw error;
  }
};

// Delete file
export const deleteFile = async (docId: string) => {
  try {
    const response = await axios.delete(`${API_URL}/v1/ingest/${docId}`);
    return response.data;
  } catch (error) {
    console.error("Error deleting file:", error);
    throw error;
  }
};

// =====================================
// TYPES & CUSTOM HOOK FOR CHAT HANDLERS
// =====================================

export interface ChatMessage {
  role: string;
  content: string;
  sources?: { file_name: string; page_label?: string }[];
  isCached?: boolean;
}

export interface HistoryInteraction {
  user: string;
  assistant?: string;
}


// useChatHandlers is a custom hook that encapsulates all chat‑related state
// and handler functions.

export const useChatHandlers = () => {
  // Chat and file-related state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("RAG");


  const [currentChatId, setCurrentChatId] = useState<number | null>(null);

  const [files, setFiles] = useState<{ file_name: string; doc_id: string }[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [systemPromptInput, setSystemPromptInput] = useState("");


  const [fileToUpload, setFileToUpload] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sidebar toggle state
  const [sidebarLeftHidden, setSidebarLeftHidden] = useState(false);
  const [sidebarRightHidden, setSidebarRightHidden] = useState(false);

  // Loading states for file operations and message sending
  const [fileLoading, setFileLoading] = useState(false);
  const [messageLoading, setMessageLoading] = useState(false);

  // Ref for axios cancellation token
  const messageCancelTokenRef = useRef(axios.CancelToken.source());


  // refresh files list

  const refreshFiles = async () => {
    try {
      setFileLoading(true);
      const fileList = await fetchFiles();
      setFiles(fileList);
    } catch (error) {
      console.error("Error fetching files:", error);
    } finally {
      setFileLoading(false);
    }
  };

  useEffect(() => {
    refreshFiles();
  }, []);



  const handleSendMessage = async (query?: string) => {
    const userQuery = query !== undefined ? query : input;
    if (!userQuery.trim() || messageLoading) return;
    // if (mode !== "Basic" && files.length === 0) {
    //   alert("Please upload a file first.");
    //   return;
    // }
    setInput("");

    setMessages((prev) => [
      ...prev,
      { role: "user", content: userQuery, isCached: false },
      { role: "assistant", content: '<div className="spinner2"></div>', isCached: false },
    ]);

    setMessageLoading(true);
    messageCancelTokenRef.current = axios.CancelToken.source();

    const fileIDsToUse =
      selectedFiles.length === 0 ? files.map((file) => file.doc_id) : selectedFiles;

    // Preserve only the last 20 messages as context, excluding the retried query if needed
    const fullHistory: ChatMessage[] = [...messages, { role: "user", content: userQuery }];
    const limitedHistory = fullHistory.slice(-20);

    let response: any;
    let botResponse = "";
    try {
      if (mode === "Summarize") {
        response = await summarize_message(
          limitedHistory,
          fileIDsToUse,
          { cancelToken: messageCancelTokenRef.current.token },
          systemPromptInput
        );
        botResponse = response.summary || "No summary available.";
      } else if (mode === "Search") {
        response = await search_message(limitedHistory, fileIDsToUse, {
          cancelToken: messageCancelTokenRef.current.token,
        });
        if (response.data) {
          const sources: Record<string, string[]> = response.data
            .filter((src: any) => src.score > 0.5)
            .reduce((acc: Record<string, string[]>, src: any) => {
              const docName: string = src.document.doc_metadata.file_name;
              let lineText: string = src.text.trim().replace(/\n{2,}/g, "\n");
              if (!acc[docName]) {
                acc[docName] = [];
              }
              acc[docName].push(lineText);
              return acc;
            }, {});
          if (Object.keys(sources).length > 0) {
            botResponse =
              "Relevant Excerpts:<br/><br/>" +
              Object.entries(sources)
                .map(([docName, lines]) => {
                  const numberedLines = lines
                    .map((line, index) => `${index + 1}. ${line}`)
                    .join("<br/><br/>");
                  return `${numberedLines}<strong><br/>----------------------------------------------------------------<br/>Source:</strong> ${docName}<strong><br/>----------------------------------------------------------------</strong>`;
                })
                .join("<br/><br/>");
          } else {
            botResponse = "No relevant context found.";
          }
        } else {
          botResponse = "No relevant context found.";
        }
      } else if (mode === "RAG" || mode === "AgenticBot" || mode === "ToolCalling") {
        response = await rag_basicmessage(
          limitedHistory,
          mode,
          fileIDsToUse,
          { cancelToken: messageCancelTokenRef.current.token },
          systemPromptInput
        );
        botResponse = response.choices?.[0]?.message?.content || "";
        if (response.choices && response.choices[0] && response.choices[0].sources) {
          const sourceSet = new Set<string>();
          response.choices[0].sources
            .filter((src: any) => src.score > 0.5)
            .forEach((src: any) => {
              const docName: string = src.document.doc_metadata.file_name;
              sourceSet.add(docName);
            });
          if (sourceSet.size > 0) {
            botResponse += "<br/><br/><strong>Sources:</strong> " + Array.from(sourceSet).join(", ");
          }
        }
      } else {
        response = await rag_basicmessage(
          limitedHistory,
          "Basic",
          [],
          { cancelToken: messageCancelTokenRef.current.token },
          systemPromptInput
        );
        botResponse = response.choices?.[0]?.message?.content || "No response received.";
      }
      const newResponse = `${botResponse}<br/>`;
      setMessages((prev) => {
        const newMsgs = [...prev];
        newMsgs[newMsgs.length - 1] = { role: "assistant", content: newResponse, isCached: false };
        return newMsgs;
      });
    } catch (error: any) {
      if (axios.isCancel(error)) {
        console.log("Request cancelled:", error.message);
        setMessages((prev) => {
          const newMsgs = [...prev];
          if (newMsgs[newMsgs.length - 1].role === "assistant") {
            newMsgs.pop();
          }
          return newMsgs;
        });
      } else {
        console.error("Error sending message:", error);
      }
    } finally {
      setMessageLoading(false);
    }
  };


  // ----------------------------
  // Handler: retry last message

  const handleRetry = async () => {
    if (messageLoading || messages.length < 1) return;

    // Clone the current messages array
    const newMessages = [...messages];
    let lastUserQuery = "";

    // Identify and remove the last user query and its corresponding assistant response.
    const lastMessage = newMessages[newMessages.length - 1];
    const secondLastMessage = newMessages[newMessages.length - 2];

    if (lastMessage?.role === "assistant" && secondLastMessage?.role === "user") {
      lastUserQuery = secondLastMessage.content;
      newMessages.pop(); // Remove assistant response
      newMessages.pop(); // Remove user query
    } else if (lastMessage?.role === "user") {
      lastUserQuery = lastMessage.content;
      newMessages.pop(); // Remove the lone user query
    }

    if (!lastUserQuery.trim()) return; // Ensure valid query

    // Update the messages state so that the retried pair is excluded.
    setMessages(newMessages);

    // Now call handleSendMessage with the retried query.
    await handleSendMessage(lastUserQuery);
  };
  // ----------------------------
  // Handler: undo last message
  // ----------------------------
  const handleUndo = () => {
    if (messageLoading || messages.length < 1) return;

    setMessages((prev) => {
      const newMessages = [...prev];
      const lastMessage = newMessages[newMessages.length - 1];
      const secondLastMessage = newMessages[newMessages.length - 2];

      if (lastMessage.role === "assistant" && secondLastMessage?.role === "user") {
        return newMessages.slice(0, newMessages.length - 2);
      } else if (lastMessage.role === "user") {
        return newMessages.slice(0, newMessages.length - 1);
      }

      return newMessages;
    });

    setInput("");
  };

  // ----------------------------
  // Handler: change chat mode
  // ----------------------------
  const handleModeChange = (newMode: string) => {
    if (messageLoading) return;
    setMode(newMode);
    // Preserve full history when changing modes
    setMessages((prevMessages) => [...prevMessages]);
  };


  // ----------------------------
  // Handler: toggle file selection
  // ----------------------------
  const toggleFileSelection = (doc_id: string) => {
    if (selectedFiles.includes(doc_id)) {
      setSelectedFiles(selectedFiles.filter((id) => id !== doc_id));
    } else {
      setSelectedFiles([...selectedFiles, doc_id]);
    }
  };

  // ----------------------------
  // Handler: de-select files
  // ----------------------------
  const handleDeselectFile = () => {
    setSelectedFiles([]);
  };

  // ----------------------------
  // Handler: delete selected files
  // ----------------------------
  const handleDeleteSelectedFiles = async () => {
    try {
      setFileLoading(true);
      for (const docId of selectedFiles) {
        await deleteFile(docId);
      }
      await refreshFiles();
      setSelectedFiles([]);
    } catch (error) {
      console.error("Error deleting selected files:", error);
    } finally {
      setFileLoading(false);
    }
  };

  // ----------------------------
  // Handler: delete all files
  // ----------------------------
  const handleDeleteAllFiles = async () => {
    try {
      setFileLoading(true);
      for (const file of files) {
        await deleteFile(file.doc_id);
      }
      await refreshFiles();
      setSelectedFiles([]);
    } catch (error) {
      console.error("Error deleting all files:", error);
    } finally {
      setFileLoading(false);
    }
  };

  // ----------------------------
  // Handler: clear chat history
  // ----------------------------
  const handleClearChat = () => {
    setMessages([]);
  };

  // ----------------------------
  // Handler: file input change (upload file)
  // ----------------------------
  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setFileToUpload(file);
      try {
        setFileLoading(true);
        await uploadFile(file);
        setFileToUpload(null);
        await refreshFiles();
      } catch (error) {
        console.error("Error uploading file:", error);
      } finally {
        setFileLoading(false);
      }
    }
  };

  // ----------------------------
  // Handler: toggle sidebar visibility
  // ----------------------------
  const toggleSidebarLeft = () => {    setSidebarLeftHidden((prev) => !prev);  };
  const toggleSidebarRight = () => {    setSidebarRightHidden((prev) => !prev);  };
  // ----------------------------
  // Handler: stop in-progress API call
  // ----------------------------
  const handleStopMessage = () => {
    if (messageLoading) {
      messageCancelTokenRef.current.cancel("Request cancelled by user.");
      setMessageLoading(false);
      setMessages((prev) => {
        const newMsgs = [...prev];
        if (newMsgs[newMsgs.length - 1].role === "assistant") {
          newMsgs.pop();
        }
        return newMsgs;
      });
    }
  };

  const handleDeleteFile = async (doc_id: string) => {
    try {
      setFileLoading(true);
      await deleteFile(doc_id);
      // Remove the file from selectedFiles if it exists:
      setSelectedFiles((prev) => prev.filter((id) => id !== doc_id));
      await refreshFiles();
    } catch (error) {
      console.error("Failed to delete file:", error);
    } finally {
      setFileLoading(false);
    }
  };

  return {
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
    currentChatId,      // New: current chat id state
    setCurrentChatId,
    refreshFiles,   // New: setter for current chat id
  };
};
