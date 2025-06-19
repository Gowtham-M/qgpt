from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Request, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
import uuid
from datetime import datetime
import shutil
from pathlib import Path
import requests
import json
import base64
from pydantic import BaseModel

from qgpt_core.components.llm.llm_component import LLMComponent
from qgpt_core.server.utils.auth import authenticated

# Create assets directory if it doesn't exist
ASSETS_DIR = Path("d:/qgptrepo/fisec/QGPT/assets/images")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

images_router = APIRouter(prefix="/v1/images", dependencies=[Depends(authenticated)])


# Pydantic models for chat functionality
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ImageChatRequest(BaseModel):
    image_path: str
    message: str
    chat_history: Optional[List[ChatMessage]] = None


@images_router.post("/chat")
async def chat_about_image(
    request: Request,
    chat_request: ImageChatRequest
):
    """
    Chat about an uploaded image with conversation history support, always using the vision model.
    """
    try:
        # Verify image exists
        if not os.path.exists(chat_request.image_path):
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Always use the vision model for this chat
        model_name = "qwen2.5vl:3b"
        
        # Get LLM component from dependency injection
        llm_component: LLMComponent = request.state.injector.get(LLMComponent)
        if hasattr(llm_component, 'llm') and hasattr(llm_component.llm, 'base_url'):
            base_url = llm_component.llm.base_url
        else:
            base_url = "http://localhost:11434"  # Default Ollama URL
        
        # Read and encode the image as base64
        with open(chat_request.image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Build conversation context with chat history
        conversation_context = ""
        if chat_request.chat_history:
            conversation_context += "Previous conversation about this image:\n"
            for msg in chat_request.chat_history:
                conversation_context += f"{msg.role.capitalize()}: {msg.content}\n"
            conversation_context += "\n"
        
        # Combine context with current message
        full_prompt = conversation_context + chat_request.message
        
        # Always use the vision model for every message
        request_data = {
            "model": model_name,
            "prompt": full_prompt,
            "images": [image_data],
            "stream": False
        }
        
        print(f"[DEBUG] Image chat request - Image: {chat_request.image_path}")
        print(f"[DEBUG] Full prompt: {full_prompt[:200]}...")
        response = requests.post(
            f"{base_url}/api/generate",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            analysis_text = result.get("response", "No response available")
            return JSONResponse(
                content={
                    "success": True,
                    "response": analysis_text,
                    "image_path": chat_request.image_path,
                    "model": model_name,
                    "conversation_id": str(uuid.uuid4())
                }
            )
        else:
            raise HTTPException(status_code=500, detail=f"Ollama API error: {response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to chat about image: {str(e)}")


@images_router.post("/chat-form")
async def chat_about_image_form(
    request: Request,
    image_path: str = Form(...),
    message: str = Form(...),
    chat_history: Optional[str] = Form(None)  # JSON string of chat history
):
    """
    Chat about an uploaded image using form data (easier for frontend integration)
    """
    try:
        # Parse chat history if provided
        parsed_chat_history = None
        if chat_history:
            try:
                chat_data = json.loads(chat_history)
                parsed_chat_history = [ChatMessage(**msg) for msg in chat_data]
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[DEBUG] Failed to parse chat history: {e}")
                parsed_chat_history = None
        
        # Create chat request object
        chat_request = ImageChatRequest(
            image_path=image_path,
            message=message,
            chat_history=parsed_chat_history
        )
        
        # Use the existing chat logic
        return await chat_about_image(request, chat_request)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to chat about image: {str(e)}")


@images_router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    message: Optional[str] = Form(None)
):
    """
    Upload an image and optionally process it with vision model
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = ASSETS_DIR / unique_filename
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return the file path for frontend use
        return JSONResponse(
            content={
                "success": True,
                "file_path": str(file_path),
                "filename": unique_filename,
                "message": "Image uploaded successfully"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@images_router.post("/analyze")
async def analyze_image(
    request: Request,
    image_path: str = Form(...),
    message: Optional[str] = Form("Describe this image in detail")
):
    """
    Analyze an uploaded image using Ollama vision model
    """
    try:
        # Verify image exists
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image not found")        # Get LLM component from dependency injection
        llm_component: LLMComponent = request.state.injector.get(LLMComponent)
          # Get Ollama settings from the LLM component
        if hasattr(llm_component, 'llm') and hasattr(llm_component.llm, 'base_url'):
            base_url = llm_component.llm.base_url
        else:
            base_url = "http://localhost:11434"  # Default Ollama URL
        
        # Read and encode the image as base64
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create request data for Ollama API
        request_data = {
            "model": "qwen2.5vl:3b",
            "prompt": message,
            "images": [image_data],
            "stream": False
        }        # Make direct API call to Ollama with increased timeout
        response = requests.post(
            f"{base_url}/api/generate",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=300  # Increased timeout to 5 minutes for vision models
        )
        
        if response.status_code == 200:
            result = response.json()
            analysis_text = result.get("response", "No analysis available")
            
            return JSONResponse(
                content={
                    "success": True,
                    "analysis": analysis_text,
                    "image_path": image_path,
                    "model": "qwen2.5vl:7b"
                }
            )
        else:
            raise HTTPException(status_code=500, detail=f"Ollama API error: {response.text}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze image: {str(e)}")


@images_router.post("/upload-and-analyze")
async def upload_and_analyze_image(
    request: Request,
    file: UploadFile = File(...),
    message: Optional[str] = Form("Describe this image in detail")
):
    """
    Upload and analyze an image in one step
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Generate unique filename and save image
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = ASSETS_DIR / unique_filename
          # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Analyze the image using Ollama
        try:
            print(f"[DEBUG] Starting image analysis for file: {file_path}")
            
            # Get Ollama base URL
            llm_component: LLMComponent = request.state.injector.get(LLMComponent)
            if hasattr(llm_component, 'llm') and hasattr(llm_component.llm, 'base_url'):
                base_url = llm_component.llm.base_url
            else:
                base_url = "http://localhost:11434"  # Default Ollama URL            print(f"[DEBUG] Using Ollama URL: {base_url}")
              # Read and encode the image as base64
            with open(file_path, "rb") as image_file:
                image_bytes = image_file.read()
                
            # Check image size and potentially resize if too large
            image_size_mb = len(image_bytes) / (1024 * 1024)
            print(f"[DEBUG] Original image size: {image_size_mb:.2f} MB")
            
            # If image is larger than 10MB, we might want to resize it
            if image_size_mb > 10:
                print(f"[WARNING] Large image detected ({image_size_mb:.2f} MB), this may cause timeouts")
            
            image_data = base64.b64encode(image_bytes).decode('utf-8')
            print(f"[DEBUG] Base64 encoded size: {len(image_data)} characters")            # Create request data for Ollama API with streaming enabled
            request_data = {
                "model": "qwen2.5vl:3b",
                "prompt": message,
                "images": [image_data],
                "stream": True,  # Enable streaming to avoid timeouts
                "options": {
                    "temperature": 0.1,
                    "num_predict": 512  # Limit response length to speed up
                }
            }
            print(f"[DEBUG] Making request to: {base_url}/api/generate")
            print(f"[DEBUG] Request data: {{'model': '{request_data['model']}', 'prompt': '{request_data['prompt'][:50]}...', 'images': '[base64_data]', 'stream': {request_data['stream']}}}")
            
            # Make direct API call to Ollama with multiple timeout attempts
            timeouts = [30, 60, 120]  # Try progressively longer timeouts
            response = None
            last_error = None
            
            for timeout_duration in timeouts:
                try:
                    print(f"[DEBUG] Attempting with {timeout_duration}s timeout...")
                    response = requests.post(
                        f"{base_url}/api/generate",
                        json=request_data,
                        headers={"Content-Type": "application/json"},
                        timeout=timeout_duration
                    )
                    print(f"[DEBUG] Success with {timeout_duration}s timeout!")
                    break
                except requests.exceptions.Timeout as e:
                    last_error = e
                    print(f"[DEBUG] Timeout after {timeout_duration}s, trying next...")
                    continue
                except Exception as e:
                    last_error = e
                    print(f"[DEBUG] Error: {e}")
                    break
            
            if response is None:
                # Try with a fallback simpler prompt
                print("[DEBUG] All timeouts failed, trying with simpler prompt...")
                simple_request = {
                    "model": "qwen2.5vl:3b",
                    "prompt": "What is this?",
                    "images": [image_data],
                    "stream": False,
                    "options": {
                        "temperature": 0,
                        "num_predict": 20
                    }
                }
                try:
                    response = requests.post(
                        f"{base_url}/api/generate",
                        json=simple_request,
                        headers={"Content-Type": "application/json"},
                        timeout=90
                    )
                except Exception as fallback_error:
                    print(f"[DEBUG] Fallback also failed: {fallback_error}")
                    raise Exception(f"Vision processing failed after multiple attempts. Last error: {last_error}")
                    print(f"[DEBUG] Response status code: {response.status_code}")
            
            if response.status_code == 200:
                # Handle streaming response
                if request_data.get("stream", False):
                    full_response = ""
                    try:
                        # Process each line of the streaming response
                        for line in response.text.strip().split('\n'):
                            if line.strip():
                                try:
                                    chunk = json.loads(line)
                                    if 'response' in chunk:
                                        full_response += chunk['response']
                                    # Check if this is the final chunk
                                    if chunk.get('done', False):
                                        break
                                except json.JSONDecodeError:
                                    continue
                        analysis_text = full_response if full_response else "No analysis available"
                    except Exception as stream_error:
                        print(f"[DEBUG] Streaming parse error: {stream_error}")
                        analysis_text = f"Partial response received but parsing failed: {str(stream_error)}"
                else:
                    # Handle non-streaming response
                    result = response.json()
                    analysis_text = result.get("response", "No analysis available")
                
                print(f"[DEBUG] Final analysis text: {analysis_text[:100]}...")
                return JSONResponse(
                content={
                    "success": True,
                    "file_path": str(file_path),
                    "filename": unique_filename,
                    "analysis": analysis_text,
                    "model": "qwen2.5vl:3b"
                }
                )
            else:
                # If analysis fails, still return the uploaded file info
                return JSONResponse(
                    content={
                        "success": True,
                        "file_path": str(file_path),
                        "filename": unique_filename,
                        "analysis": f"Image uploaded successfully, but analysis failed: {response.text}",
                        "model": "qwen2.5vl:3b"
                    }
                )
        
        except Exception as analysis_error:
            # If analysis fails, still return the uploaded file info
            return JSONResponse(
                content={
                    "success": True,
                    "file_path": str(file_path),
                    "filename": unique_filename,
                    "analysis": f"Image uploaded successfully, but analysis failed: {str(analysis_error)}",
                    "model": "qwen2.5vl:3b"
                }
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload and analyze image: {str(e)}")


@images_router.get("/list")
async def list_images():
    """
    List all uploaded images
    """
    try:
        images = []
        for image_file in ASSETS_DIR.glob("*"):
            if image_file.is_file():
                stat = image_file.stat()
                images.append({
                    "filename": image_file.name,
                    "path": str(image_file),
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
        
        return JSONResponse(
            content={
                "success": True,
                "images": images,
                "count": len(images)
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list images: {str(e)}")


@images_router.delete("/{filename}")
async def delete_image(filename: str):
    """
    Delete an uploaded image
    """
    try:
        file_path = ASSETS_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")
        
        file_path.unlink()
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Image {filename} deleted successfully"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete image: {str(e)}")
