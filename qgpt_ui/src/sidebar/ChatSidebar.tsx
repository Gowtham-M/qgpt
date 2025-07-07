import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  FiFolderPlus,
  FiSearch,
  FiX,
  FiTrash2,
  FiEdit2,
} from "react-icons/fi";
import { MdKeyboardArrowDown, MdKeyboardArrowRight } from "react-icons/md";

import "./sidebar.css";

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

interface ChatSidebarProps {
  mode: string; // e.g., "RAG", "Basic", etc.
  currentChatId: number | null;
  onSelectChat: (chat: Chat | null) => void; // Allow null as an argument
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({
  mode,
  currentChatId,
  onSelectChat,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [chatData, setChatData] = useState<ChatData>({ folders: [], ungroupedChats: [] });
  const [folderOpen, setFolderOpen] = useState<Record<number, boolean>>({});
  const [dragOverFolder, setDragOverFolder] = useState<number | null>(null);
  const [editingChatId, setEditingChatId] = useState<number | null>(null);
  const [editingChatName, setEditingChatName] = useState("");
  const [editingFolderId, setEditingFolderId] = useState<number | null>(null);
  const [editingFolderName, setEditingFolderName] = useState("");

  // Load chat data from localStorage for the current mode
  useEffect(() => {
    const storedData = localStorage.getItem(`chatData_${mode}`);
    if (storedData) {
      setChatData(JSON.parse(storedData));
    } else {
      setChatData({ folders: [], ungroupedChats: [] });
    }
  }, [mode]);

  // Update localStorage whenever chatData changes
  useEffect(() => {
    localStorage.setItem(`chatData_${mode}`, JSON.stringify(chatData));
  }, [chatData, mode]);

  // Auto-open folders that contain matching chats when searching
  useEffect(() => {
    if (searchTerm.trim() !== "") {
      const FoldersOpen: Record<number, boolean> = {};
      chatData.folders.forEach((folder) => {
        const hasMatchingChats = folder.chats.some((chat) =>
          chat.name.toLowerCase().includes(searchTerm.toLowerCase())
        );
        if (hasMatchingChats) FoldersOpen[folder.id] = true;
      });
      setFolderOpen(FoldersOpen);
    }
  }, [searchTerm, chatData.folders]);

  //unique name for a chat (Untitled, Untitled(2), …)
  const getUniqueChatName = useCallback((): string => {
    const baseName = "Untitled";
    let count = 1;
    const allChats = [
      ...chatData.ungroupedChats,
      ...chatData.folders.flatMap((folder) => folder.chats),
    ];
    while (
      allChats.some(
        (chat) => chat.name === (count === 1 ? baseName : `${baseName}(${count})`)
      )
    ) {
      count++;
    }
    return count === 1 ? baseName : `${baseName}(${count})`;
  }, [chatData]);


  // Create a new chat (initially ungrouped)
  const handleNewChat = useCallback(() => {
    const newChat: Chat = {
      id: Date.now(),
      name: getUniqueChatName(),
      messages: [],
    };
    setChatData((prev) => ({
      ...prev,
      ungroupedChats: [newChat, ...prev.ungroupedChats],
    }));
    onSelectChat(newChat);
  }, [getUniqueChatName, onSelectChat]);

  const getUniqueFolderName = useCallback((): string => {
    const baseName = "New Folder";
    let count = 1;
    const allFolders = chatData.folders; // Directly use folders

    while (
      allFolders.some(
        (folder) => folder.name === (count === 1 ? baseName : `${baseName}(${count})`)
      )
    ) {
      count++;
    }
    return count === 1 ? baseName : `${baseName}(${count})`;
  }, [chatData.folders]);

  // Create a new folder
  const handleNewFolder = useCallback(() => {
    const newFolder: Folder = {
      id: Date.now(),
      name: getUniqueFolderName(),
      chats: [],
    };
    setChatData((prev) => ({
      ...prev,
      folders: [newFolder, ...prev.folders],
    }));
  }, [getUniqueFolderName]);

  // Delete a chat (from both ungrouped and folder lists)
  const handleDeleteChat = useCallback((chatId: number) => {
    setChatData((prev) => {
      const updatedUngrouped = prev.ungroupedChats.filter((chat) => chat.id !== chatId);
      const updatedFolders = prev.folders.map((folder) => ({
        ...folder,
        chats: folder.chats.filter((chat) => chat.id !== chatId),
      }));
      return { folders: updatedFolders, ungroupedChats: updatedUngrouped };
    });
    // Clear selection if the deleted chat is currently selected
    if (currentChatId === chatId) {
      onSelectChat(null);
    }
  }, [currentChatId, onSelectChat]);


  // Inline renaming for a chat
  const startEditingChat = useCallback((chat: Chat) => {
    setEditingChatId(chat.id);
    setEditingChatName(chat.name);
  }, []);

  const saveChatName = useCallback((chatId: number) => {
    if (editingChatName.trim() === "") {
      const allChats = [
        ...chatData.ungroupedChats,
        ...chatData.folders.flatMap((folder) => folder.chats),
      ];
      const currentChat = allChats.find((chat) => chat.id === chatId);
      setEditingChatName(currentChat ? currentChat.name : "");
      setEditingChatId(null);
      return;
    }
    setChatData((prev) => {
      const updateChat = (chat: Chat) =>
        chat.id === chatId ? { ...chat, name: editingChatName } : chat;
      const updatedUngrouped = prev.ungroupedChats.map(updateChat);
      const updatedFolders = prev.folders.map((folder) => ({
        ...folder,
        chats: folder.chats.map(updateChat),
      }));
      return { folders: updatedFolders, ungroupedChats: updatedUngrouped };
    });
    setEditingChatId(null);
    setEditingChatName("");
  }, [editingChatName, chatData]);

  // Inline renaming for a folder
  const startEditingFolder = useCallback((folder: Folder) => {
    setEditingFolderId(folder.id);
    setEditingFolderName(folder.name);
  }, []);

  const saveFolderName = useCallback((folderId: number) => {
    if (editingFolderName.trim() === "") {
      const currentFolder = chatData.folders.find((folder) => folder.id === folderId);
      setEditingFolderName(currentFolder ? currentFolder.name : "");
      setEditingFolderId(null);
      return;
    }
    setChatData((prev) => {
      const updatedFolders = prev.folders.map((folder) =>
        folder.id === folderId ? { ...folder, name: editingFolderName } : folder
      );
      return { ...prev, folders: updatedFolders };
    });
    setEditingFolderId(null);
    setEditingFolderName("");
  }, [editingFolderName, chatData.folders]);

  // Delete a folder (optionally moving its chats to ungrouped)
  const handleDeleteFolder = useCallback((folderId: number) => {
    // Find the folder to be deleted
    const folder = chatData.folders.find((f) => f.id === folderId);
    setChatData((prev) => {
      const updatedFolders = prev.folders.filter((folder) => folder.id !== folderId);
      const updatedUngrouped = folder ? [...folder.chats, ...prev.ungroupedChats] : prev.ungroupedChats;
      return { folders: updatedFolders, ungroupedChats: updatedUngrouped };
    });
    // Clear selection if the selected chat is inside the deleted folder
    if (folder && currentChatId !== null && folder.chats.some((chat) => chat.id === currentChatId)) {
      onSelectChat(null);
    }
  }, [chatData.folders, currentChatId, onSelectChat]);


  // Drag-and-drop handlers
  const handleDragStart = useCallback((e: React.DragEvent, chatId: number) => {
    e.dataTransfer.setData("chatId", chatId.toString());
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent, targetFolderId: number | null) => {
      e.preventDefault();
      const chatId = Number(e.dataTransfer.getData("chatId"));
      const movedChat =
        chatData.folders.flatMap((folder) => folder.chats).find((chat) => chat.id === chatId) ||
        chatData.ungroupedChats.find((chat) => chat.id === chatId);
      if (!movedChat) return;
      const updatedFolders = chatData.folders.map((folder) => ({
        ...folder,
        chats: folder.chats.filter((chat) => chat.id !== chatId),
      }));
      const updatedUngrouped = chatData.ungroupedChats.filter((chat) => chat.id !== chatId);
      if (targetFolderId !== null) {
        const finalFolders = updatedFolders.map((folder) => {
          if (folder.id === targetFolderId) {
            return { ...folder, chats: [movedChat, ...folder.chats] };
          }
          return folder;
        });
        setChatData({ folders: finalFolders, ungroupedChats: updatedUngrouped });
      } else {
        setChatData({
          folders: updatedFolders,
          ungroupedChats: [movedChat, ...updatedUngrouped],
        });
      }
      setDragOverFolder(null);
    },
    [chatData]
  );

  // Toggle folder open/close state
  const toggleFolderOpen = useCallback((folderId: number) => {
    setFolderOpen((prev) => ({ ...prev, [folderId]: !prev[folderId] }));
  }, []);

  const clearAllConversations = useCallback(() => {
    if (window.confirm("Are you sure you want to clear all conversations?")) {
      setChatData({ folders: [], ungroupedChats: [] });
    }
  }, []);

  // Memoized search filtering
  const filteredUngroupedChats = useMemo(
    () =>
      chatData.ungroupedChats.filter((chat) =>
        chat.name.toLowerCase().includes(searchTerm.toLowerCase())
      ),
    [chatData.ungroupedChats, searchTerm]
  );
  const totalFolderMatches = useMemo(
    () =>
      chatData.folders.reduce((total, folder) => {
        const folderMatches = folder.chats.filter((chat) =>
          chat.name.toLowerCase().includes(searchTerm.toLowerCase())
        );
        return total + folderMatches.length;
      }, 0),
    [chatData.folders, searchTerm]
  );
  const totalMatches = filteredUngroupedChats.length + totalFolderMatches;

  // component for rendering a Chat Item
  const ChatItem: React.FC<{ chat: Chat }> = ({ chat }) => (
    <div
      className={`chat-item ${currentChatId === chat.id ? "selected" : ""}`}
      draggable
      onDragStart={(e) => handleDragStart(e, chat.id)}
      onClick={() => onSelectChat(chat)}
      onDoubleClick={() => startEditingChat(chat)}
    >
      {editingChatId === chat.id ? (
        <input
          type="text"
          value={editingChatName}
          onChange={(e) => setEditingChatName(e.target.value)}
          onBlur={() => saveChatName(chat.id)}
          onKeyDown={(e) => e.key === "Enter" && saveChatName(chat.id)}
          autoFocus
          className="rename-input"
        />
      ) : (
        <span className="ellipsis-text" title={chat.name}>{chat.name}</span>
      )}
      <span className="chat-item-icons">
        <FiEdit2
          className="icon-edit"
          onClick={(e) => {
            e.stopPropagation();
            startEditingChat(chat);
          }}
        />
        <FiTrash2
          className="icon-trash"
          onClick={(e) => {
            e.stopPropagation();
            handleDeleteChat(chat.id);
          }}
        />
      </span>
    </div>
  );

  return (
    <div className="chat-sidebar">
      {/* Header with New Chat and New Folder */}
      <div className="sidebar-header">
        <button className="new-chat-button" onClick={handleNewChat}>
          + New Chat
        </button>
        <button className="new-folder-button" onClick={handleNewFolder}>
          <FiFolderPlus size={20} />
        </button>
      </div>
      {/* Search bar */}
      <div className="sidebar-search">
        <div className="search-input-container">
          <input
            type="text"
            placeholder="Search chats..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          {searchTerm.trim() !== "" ? (
            <FiX
              className="search-icon"
              onClick={() => setSearchTerm("")}
              style={{ cursor: "pointer" }}
            />
          ) : (
            <FiSearch className="search-icon" />
          )}
        </div>
      </div>
      <div style={{ maxHeight: "20rem", overflowY: "auto", scrollbarWidth: "thin" }}>
        {/* Render Folders */}
        {chatData.folders.map((folder) => (
          <div
            key={folder.id}
            className="folder-container"
            onDragOver={(e) => {
              e.preventDefault();
              setDragOverFolder(folder.id);
            }}
            onDragLeave={() => setDragOverFolder(null)}
            onDrop={(e) => handleDrop(e, folder.id)}
          >
            <div
              className={`folder-header ${dragOverFolder === folder.id ? "drag-over" : ""}`}
              onClick={() => toggleFolderOpen(folder.id)}
            >
              {/* Separate grid cells */}
              <div className="folder-toggle">
                {folderOpen[folder.id] ? (
                  <MdKeyboardArrowDown className="folder-toggle-icon" />
                ) : (
                  <MdKeyboardArrowRight className="folder-toggle-icon" />
                )}
              </div>
              <div className="folder-name-container">
                {editingFolderId === folder.id ? (
                  <input
                    type="text"
                    value={editingFolderName}
                    onChange={(e) => setEditingFolderName(e.target.value)}
                    onBlur={() => saveFolderName(folder.id)}
                    onKeyDown={(e) => e.key === "Enter" && saveFolderName(folder.id)}
                    autoFocus
                    className="rename-input"
                  />
                ) : (
                  <div className="folder-tooltip-wrapper">
                    <span
                      className="ellipsis-text"
                      title={folder.name}
                      onDoubleClick={(e) => {
                        e.stopPropagation();
                        startEditingFolder(folder);
                      }}
                    >
                      {folder.name}
                    </span>
                    <span className="folder-tooltip">{folder.name}</span>
                  </div>
                )}
              </div>
              <div className="folder-header-right">
                <FiEdit2 className="icon-edit" onClick={(e) => { e.stopPropagation(); startEditingFolder(folder); }} />
                <FiTrash2 className="icon-trash" color="white" onClick={(e) => { e.stopPropagation(); handleDeleteFolder(folder.id); }} />
              </div>
            </div>
            {folderOpen[folder.id] &&
              folder.chats
                .filter((chat) =>
                  chat.name.toLowerCase().includes(searchTerm.toLowerCase())
                )
                .map((chat) => <ChatItem key={chat.id} chat={chat} />)}
          </div>

        ))}
        {/* Ungrouped Chats */}
        <div className="ungrouped-chats" onDragOver={(e) => e.preventDefault()} onDrop={(e) => handleDrop(e, null)}        >
          {filteredUngroupedChats.map((chat) => (
            <ChatItem key={chat.id} chat={chat} />
          ))}
        </div>
        {/* No Results Found */}
        {searchTerm.trim() !== "" && totalMatches === 0 && (
          <div className="no-results" style={{ textAlign: "center", marginTop: "1rem", color: "#888" }}>
            No results found
          </div>
        )}
      </div>
      {/* Clear All Conversations Button */}
      <div className="clear-all-container">
        <button className="clear-all-button" onClick={clearAllConversations}>
          <FiTrash2 className="icon-trash" color="white"/> Clear All Conversations
        </button>
      </div>
    </div>
  );
};

export default ChatSidebar;
