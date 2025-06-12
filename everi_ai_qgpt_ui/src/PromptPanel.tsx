import React, { useState, useEffect, useCallback } from "react";
import { Modal, Button, Form } from "react-bootstrap";
import {
  FiPlus,
  FiFolder,
  FiEdit,
  FiTrash,
  FiChevronDown,
  FiChevronRight,
} from "react-icons/fi";
import { DragDropContext, Droppable, Draggable } from "react-beautiful-dnd";
import { Dispatch, SetStateAction } from "react";
import imgMetaAgent from "./assets/MetaAgent.jpg";
import imgToolCalling from "./assets/ToolCalling.jpg";

// Base Prompt interface (used in folders and root-level prompts)
interface Prompt {
  id: number;
  name: string;
  content: string;
  description: string;
}

// Extended interface for total prompts (includes folder path)
interface TotalPrompt extends Prompt {
  path: string; // Ensures that path is always defined in totalPrompts
}

interface Folder {
  id: number;
  name: string;
  prompts: Prompt[];
}

interface PromptPanelProps {
  prompts: Prompt[]; // Root-level prompts
  folders: Folder[];
  totalPrompts: TotalPrompt[]; // Includes path
  setTotalPrompts: Dispatch<SetStateAction<TotalPrompt[]>>;
  addFolder: (name: string) => void;
  addPrompt: (newPrompt: Prompt) => void;
  addPromptToFolder: (folderId: number, newPrompt: Prompt) => void;
  updatePrompt: (updatedPrompt: Prompt) => void;
  updateFolder: (folderId: number, newName: string) => void;
  deletePrompt: (promptId: number) => void;
  deleteFolder: (folderId: number) => void;
}

const PromptPanel: React.FC<PromptPanelProps> = ({
  prompts,
  folders,
  totalPrompts,
  setTotalPrompts,
  addFolder,
  addPrompt,
  addPromptToFolder,
  updatePrompt,
  updateFolder,
  deletePrompt,
  deleteFolder,
}) => {
  const [showModal, setShowModal] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [currentPrompt, setCurrentPrompt] = useState<Prompt | null>(null);
  const [showFolderModal, setShowFolderModal] = useState(false);
  const [folderName, setFolderName] = useState("");
  const [selectedFolderId, setSelectedFolderId] = useState<number | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<number[]>([]);

  const updateTotalPrompts = useCallback(() => {
    const folderPrompts = folders.flatMap((folder) =>
      folder.prompts.map((prompt) => ({
        ...prompt,
        path: `${folder.name}/${prompt.name}`,
      }))
    );

    const rootPrompts = prompts.map((prompt) => ({
      ...prompt,
      path: prompt.name,
    }));

    setTotalPrompts([...rootPrompts, ...folderPrompts]);
  }, [folders, prompts, setTotalPrompts]);

  useEffect(() => {
    updateTotalPrompts();
  }, [updateTotalPrompts]);

  const toggleFolder = (folderId: number) => {
    setExpandedFolders((prev) =>
      prev.includes(folderId)
        ? prev.filter((id) => id !== folderId)
        : [...prev, folderId]
    );
  };

  const openPromptModal = (prompt?: Prompt, folderId?: number) => {
    if (prompt) {
      setCurrentPrompt(prompt);
      setIsEditing(true);
    } else {
      setCurrentPrompt({
        id: Date.now(),
        name: "",
        content: "",
        description: "",
      });
      setIsEditing(false);
      setSelectedFolderId(folderId ?? null);
    }
    setShowModal(true);
  };

  const handleSavePrompt = () => {
    if (!currentPrompt || !currentPrompt.name.trim()) {
      alert("Prompt name cannot be empty.");
      return;
    }

    if (isEditing) {
      updatePrompt(currentPrompt);
    } else {
      const newPrompt = { ...currentPrompt, id: Date.now() };

      if (selectedFolderId !== null) {
        addPromptToFolder(selectedFolderId, newPrompt);
      } else {
        addPrompt(newPrompt);
      }
    }

    updateTotalPrompts();
    setShowModal(false);
    setSelectedFolderId(null);
  };

  const handleDeletePrompt = (promptId: number) => {
    deletePrompt(promptId);
    updateTotalPrompts();
  };

  const openFolderModal = (folderId?: number) => {
    if (folderId !== undefined) {
      const folder = folders.find((f) => f.id === folderId);
      if (folder) setFolderName(folder.name);
    } else {
      setFolderName("");
    }
    setSelectedFolderId(folderId ?? null);
    setShowFolderModal(true);
  };

  const handleSaveFolder = () => {
    if (folderName.trim()) {
      if (selectedFolderId !== null) {
        updateFolder(selectedFolderId, folderName.trim());
      } else {
        addFolder(folderName.trim());
      }
      setShowFolderModal(false);
    }
  };
  const onDragEnd = (result: any) => {
    const { source, destination } = result;
    if (!destination) return; // No destination, nothing to do

    const sourceFolder = folders.find(
      (f) => f.id.toString() === source.droppableId
    );
    const destFolder = folders.find(
      (f) => f.id.toString() === destination.droppableId
    );
    const isSourceRoot = source.droppableId === "root";
    const isDestRoot = destination.droppableId === "root";

    let movedPrompt: Prompt;

    // Handling root-level prompt movement
    if (isSourceRoot) {
      movedPrompt = prompts[source.index];
      prompts.splice(source.index, 1); // Remove the prompt from root
    } else if (sourceFolder) {
      movedPrompt = sourceFolder.prompts[source.index];
      sourceFolder.prompts.splice(source.index, 1); // Remove from folder
    } else {
      return;
    }

    // If moved to root
    if (isDestRoot) {
      // Ensure it's not a duplicate before adding to the root level
      if (!prompts.some((p) => p.id === movedPrompt.id)) {
        prompts.splice(destination.index, 0, movedPrompt); // Add to root
      }
    } else if (destFolder) {
      // Prevent duplication by checking if the prompt is already in the folder
      if (!destFolder.prompts.some((p) => p.id === movedPrompt.id)) {
        destFolder.prompts.splice(destination.index, 0, movedPrompt); // Add to folder
      }
    }

    // Update the source folder if it has prompts left
    if (sourceFolder && sourceFolder.prompts.length > 0) {
      updateFolder(sourceFolder.id, sourceFolder.name); // Update folder state
    }

    // Update the destination folder after the prompt was added
    if (destFolder) {
      updateFolder(destFolder.id, destFolder.name); // Update folder state
    }

    // Update the total prompts list
    const updatedTotalPrompts: TotalPrompt[] = [
      ...prompts.map((prompt) => ({
        ...prompt,
        path: prompt.name, // Root-level prompts have only the name as path
      })),
      ...folders.flatMap((folder) =>
        folder.prompts.map((prompt) => ({
          ...prompt,
          path: `${folder.name}/${prompt.name}`, // Folder structure
        }))
      ),
    ];

    setTotalPrompts(updatedTotalPrompts);
  };

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <div className="section">
        <label>
          <strong>Tone Analyzer</strong>
        </label>
        <div
          className="border-0 rounded"
          style={{ height: "320px", overflowY: "auto", scrollbarWidth: "thin" }}
        >
          <div className="d-flex gap-2 mb-3">
            <Button
              variant="secondary"
              style={{ fontSize: "13px", padding: "6px 6px" }}
              onClick={() => setShowFolderModal(true)}
            >
              <FiFolder /> <FiPlus />
            </Button>
            <Button
              variant="primary"
              style={{ fontSize: "13px", padding: "6px 6px" }}
              onClick={() => {
                // Reset the current prompt before opening the modal
                setCurrentPrompt(null);
                setIsEditing(false); // Ensure it's not in edit mode
                setShowModal(true); // Open the modal
              }}
            >
              New Tone <FiPlus />
            </Button>
          </div>
          <Droppable droppableId="root">
            {(provided) => (
              <div
                {...provided.droppableProps}
                ref={provided.innerRef}
                className="mt-3 p-2 border rounded"
                style={{ marginBottom: "7px" }}
              >
                {prompts.map((prompt, index) => (
                  <Draggable
                    key={prompt.id}
                    draggableId={prompt.id.toString()}
                    index={index}
                  >
                    {(provided) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        {...provided.dragHandleProps}
                        className="d-flex align-items-center mt-2"
                      >
                        <span
                          style={{ cursor: "pointer" }}
                          onClick={() => openPromptModal(prompt)}
                        >
                          {prompt.name}
                        </span>
                        <Button
                          variant="outline-danger"
                          size="sm"
                          className="ms-auto"
                          onClick={() => handleDeletePrompt(prompt.id)}
                        >
                          <FiTrash />
                        </Button>
                      </div>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
              </div>
            )}
          </Droppable>
          {folders.map((folder) => (
            <div key={folder.id} className="mb-3 p-2 border rounded">
              <div className="d-flex align-items-center">
                <span
                  onClick={() => toggleFolder(folder.id)}
                  style={{ cursor: "pointer" }}
                >
                  {expandedFolders.includes(folder.id) ? (
                    <FiChevronDown />
                  ) : (
                    <FiChevronRight />
                  )}
                </span>
                <strong className="ms-2">{folder.name}</strong>
                <Button
                  variant="outline-secondary"
                  size="sm"
                  className="ms-auto"
                  onClick={() => openFolderModal(folder.id)}
                >
                  <FiEdit />
                </Button>
                <Button
                  variant="outline-danger"
                  size="sm"
                  className="ms-2"
                  onClick={() => deleteFolder(folder.id)}
                >
                  <FiTrash />
                </Button>
              </div>
              {expandedFolders.includes(folder.id) && (
                <Droppable droppableId={folder.id.toString()}>
                  {(provided) => (
                    <div
                      {...provided.droppableProps}
                      ref={provided.innerRef}
                      className="ms-4 mt-2 border-start ps-2"
                    >
                      <Button
                        size="sm"
                        variant="outline-primary"
                        onClick={() => {
                          // Reset the current prompt before opening the modal
                          setCurrentPrompt(null);
                          setIsEditing(false); // Ensure it's not in edit mode
                          openPromptModal(undefined, folder.id); // Open the modal for the new prompt in the folder
                        }}
                      >
                        <FiPlus /> New Tone
                      </Button>

                      {folder.prompts.map((prompt, index) => (
                        <Draggable
                          key={prompt.id}
                          draggableId={prompt.id.toString()}
                          index={index}
                        >
                          {(provided) => (
                            <div
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              {...provided.dragHandleProps}
                              className="d-flex align-items-center mt-2"
                            >
                              <span
                                style={{ cursor: "pointer" }}
                                onClick={() => openPromptModal(prompt)}
                              >
                                {prompt.name}
                              </span>
                              <Button
                                variant="outline-danger"
                                size="sm"
                                className="ms-auto"
                                onClick={() => deletePrompt(prompt.id)}
                              >
                                <FiTrash />
                              </Button>
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              )}
            </div>
          ))}
        </div>
      </div>
      {/* Prompt Edit/Add Modal */}
      <Modal show={showModal} onHide={() => setShowModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>{isEditing ? "Edit Tone" : "Add Tone"}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form.Group className="mb-2">
            <Form.Label>Name</Form.Label>
            <Form.Control
              type="text"
              value={currentPrompt?.name || ""}
              onChange={(e) =>
                setCurrentPrompt((prev) => ({
                  ...prev!,
                  name: e.target.value,
                }))
              }
            />
          </Form.Group>
          <Form.Group className="mb-2">
            <Form.Label>Description</Form.Label>
            <Form.Control
              type="text"
              value={currentPrompt?.description || ""}
              onChange={(e) =>
                setCurrentPrompt((prev) => ({
                  ...prev!,
                  description: e.target.value,
                }))
              }
            />
          </Form.Group>
          <Form.Group>
            <Form.Label>Prompt</Form.Label>
            <Form.Control
              as="textarea"
              rows={3}
              value={currentPrompt?.content || ""}
              onChange={(e) =>
                setCurrentPrompt((prev) => ({
                  ...prev!,
                  content: e.target.value,
                }))
              }
            />
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSavePrompt}>
            Save
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Folder Name Modal */}
      <Modal show={showFolderModal} onHide={() => setShowFolderModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>
            {selectedFolderId ? "Edit Folder" : "Add New Folder"}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form.Group>
            <Form.Label>Folder Name</Form.Label>
            <Form.Control
              type="text"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
            />
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowFolderModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSaveFolder}>
            Save
          </Button>
        </Modal.Footer>
      </Modal>
      <div className="section">
        <div className="header">
          <strong>QGPT Agentic Bot</strong>
        </div>
        <div className="subSection">
          <div className="try1" style={{ gap: "10px" }}>
            <img src={imgMetaAgent} alt="icon" width="20" height="20" />
            <strong>&nbsp;&nbsp;Meta Agent</strong>
            <span className="bottom-right-text">Coming soon...</span>
          </div>
        </div>
        <div className="subSection">
          <div className="try1" style={{ gap: "10px" }}>
            <img src={imgToolCalling} alt="icon" width="20" height="20" />
            <strong>&nbsp;&nbsp;Tool Calling</strong>
            <span className="bottom-right-text">Coming soon...</span>
          </div>
        </div>
      </div>
    </DragDropContext>
  );
};

export default PromptPanel;
