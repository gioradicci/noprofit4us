<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { supabase } from '../supabase'
import Button from 'primevue/button'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  label: {
    type: String,
    default: 'Immagine'
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'uploaded'])



// State
const fileInput = ref(null)
const previewUrl = ref('')
const isEditing = ref(false)
const isUploading = ref(false)
const imageSrc = ref('')
const zoom = ref(1.0)

// Cropping coordinates (relative to the image's original dimensions)
const imageEl = ref(null)
const canvasRef = ref(null)

// Drag & Drop / Touch pan state
const isDragging = ref(false)
const startX = ref(0)
const startY = ref(0)
const offsetX = ref(0) // offset from center in pixels
const offsetY = ref(0)

// Watch for initial value
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    // If it starts with /static, it's relative to the backend
    previewUrl.value = newVal.startsWith('http') ? newVal : `${import.meta.env.VITE_API_URL}${newVal}`
  } else {
    previewUrl.value = ''
  }
}, { immediate: true })

// Cleanup object URLs to avoid memory leaks
let objectUrlToCleanup = ''
function cleanup() {
  if (objectUrlToCleanup) {
    URL.revokeObjectURL(objectUrlToCleanup)
    objectUrlToCleanup = ''
  }
}
onUnmounted(cleanup)

function triggerSelectFile() {
  fileInput.value.click()
}

function onFileChange(event) {
  const file = event.target.files[0]
  if (!file) return

  cleanup()
  const reader = new FileReader()
  reader.onload = (e) => {
    imageSrc.value = e.target.result
    isEditing.value = true
    zoom.value = 1.0
    offsetX.value = 0
    offsetY.value = 0
  }
  reader.readAsDataURL(file)
  
  // Reset file input so same file can be selected again
  event.target.value = ''
}

// Drag & Pan handlers
function startDrag(e) {
  isDragging.value = true
  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const clientY = e.touches ? e.touches[0].clientY : e.clientY
  startX.value = clientX - offsetX.value
  startY.value = clientY - offsetY.value
}

function onDrag(e) {
  if (!isDragging.value) return
  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const clientY = e.touches ? e.touches[0].clientY : e.clientY
  offsetX.value = clientX - startX.value
  offsetY.value = clientY - startY.value
}

function stopDrag() {
  isDragging.value = false
}

// Apply Crop and Upload
async function applyCrop() {
  if (!canvasRef.value) return
  isUploading.value = true

  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  
  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  // Calculate source rect from zoom & pan
  const img = new Image()
  img.src = imageSrc.value
  img.onload = async () => {
    // 320x480 is 2:3 aspect ratio. Let's calculate drawing parameters
    const targetWidth = 320
    const targetHeight = 480
    
    // Original dimensions
    const iw = img.width
    const ih = img.height
    
    // We fit the image into the 3:2 mask.
    // If the image is wider than 3:2, height is the constraining dimension.
    let baseScale = 1
    if (iw / ih > targetWidth / targetHeight) {
      // Image is wider
      baseScale = targetHeight / ih
    } else {
      // Image is taller or exact
      baseScale = targetWidth / iw
    }
    
    const currentScale = baseScale * zoom.value
    
    // Width and height of the image when scaled
    const sw = iw * currentScale
    const sh = ih * currentScale
    
    // Draw the image onto the canvas, centered by default, adjusted by pan offsets
    // Destination coordinates on the 480x320 canvas:
    const dx = (targetWidth - sw) / 2 + offsetX.value
    const dy = (targetHeight - sh) / 2 + offsetY.value
    
    ctx.drawImage(img, dx, dy, sw, sh)
    
    // Convert to Blob and Upload
    canvas.toBlob(async (blob) => {
      let finalBlob = blob
      let filename = 'image.webp'
      
      // Fallback check: if WebP compression is not supported by the browser, fallback to JPEG
      if (blob && blob.type !== 'image/webp') {
        await new Promise((resolve) => {
          canvas.toBlob((jpgBlob) => {
            finalBlob = jpgBlob
            filename = 'image.jpg'
            resolve()
          }, 'image/jpeg', 0.8)
        })
      }
      
      try {
        const token = (await supabase.auth.getSession()).data.session?.access_token
        const formData = new FormData()
        formData.append('file', finalBlob, filename)
        
        const response = await fetch(import.meta.env.VITE_API_URL + '/gadgets/upload-image', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`
          },
          body: formData
        })
        
        if (response.ok) {
          const data = await response.json()
          emit('update:modelValue', data.image_path)
          emit('uploaded', data.image_path)
          
          previewUrl.value = `${import.meta.env.VITE_API_URL}${data.image_path}`
          isEditing.value = false
        } else {
          alert("Impossibile caricare l'immagine sul server.")
        }
      } catch (err) {
        console.error(err)
        alert("Errore di connessione durante l'upload.")
      } finally {
        isUploading.value = false
      }
    }, 'image/webp', 0.8)
  }
}

function removeImage() {
  emit('update:modelValue', '')
  emit('uploaded', '')
  previewUrl.value = ''
}

function cancelEdit() {
  isEditing.value = false
}
</script>

<template>
  <div class="image-upload-wrapper flex flex-column align-items-center gap-3">
    <!-- View / Preview Mode -->
    <div v-if="!isEditing" class="flex flex-column align-items-center gap-2 w-full">
      <div :class="['preview-container border-2 border-dashed border-round flex align-items-center justify-content-center overflow-hidden position-relative cursor-pointer', compact ? 'compact-preview' : '']" @click="triggerSelectFile" :title="compact ? 'Clicca per modificare o caricare immagine' : ''">
        <img v-if="previewUrl" :src="previewUrl" alt="Preview" class="preview-image" />
        <div v-else class="flex flex-column align-items-center text-color-secondary text-center" :class="compact ? 'p-1' : 'p-3'">
          <i class="pi pi-image mb-2" :class="compact ? 'text-sm' : 'text-3xl'"></i>
          <span v-if="!compact" class="text-xs font-semibold">{{ label }}</span>
          <span v-if="!compact" class="text-xxs text-400 mt-1">Carica o scatta foto (2:3)</span>
        </div>
      </div>
      <div v-if="previewUrl && !compact" class="flex gap-2">
        <Button label="Cambia" icon="pi pi-sync" size="small" severity="secondary" outlined @click="triggerSelectFile" />
        <Button label="Rimuovi" icon="pi pi-trash" size="small" severity="danger" outlined @click="removeImage" />
      </div>
    </div>

    <!-- Hidden native file input. Smartphone OS will automatically show camera capture + gallery options -->
    <input
      type="file"
      ref="fileInput"
      accept="image/*"
      class="hidden"
      @change="onFileChange"
    />

    <!-- Interactive Cropper Dialog/Editor overlay -->
    <div v-if="isEditing" class="cropper-overlay flex align-items-center justify-content-center p-3">
      <div class="cropper-card card shadow-5 border-round p-4 surface-card flex flex-column gap-3">
        <h4 class="m-0 text-lg font-bold text-color">Ritaglia Immagine</h4>
        <p class="text-xs text-color-secondary mt-0 mb-2">Trascina e usa lo slider per centrare l'immagine nell'area 2:3 chiara.</p>
        
        <!-- Crop viewport container -->
        <div 
          class="crop-viewport position-relative overflow-hidden border-round flex align-items-center justify-content-center"
          @mousedown="startDrag"
          @mousemove="onDrag"
          @mouseup="stopDrag"
          @mouseleave="stopDrag"
          @touchstart="startDrag"
          @touchmove="onDrag"
          @touchend="stopDrag"
        >
          <!-- Masked Image -->
          <img 
            ref="imageEl" 
            :src="imageSrc" 
            alt="To crop" 
            class="crop-image-underlay"
            :style="{
              transform: `translate(${offsetX}px, ${offsetY}px) scale(${zoom})`,
              cursor: isDragging ? 'grabbing' : 'grab'
            }"
            draggable="false"
          />
          
          <!-- Outer dim overlay -->
          <div class="crop-mask-overlay"></div>
          
          <!-- 3:2 Crop Cutout Bounding Box -->
          <div class="crop-cutout-box border-2 border-primary"></div>
        </div>

        <!-- Zoom Slider -->
        <div class="flex align-items-center gap-3 w-full">
          <i class="pi pi-minus text-xs text-color-secondary"></i>
          <input 
            type="range" 
            v-model.number="zoom" 
            min="1" 
            max="3" 
            step="0.05" 
            class="zoom-slider flex-grow-1" 
          />
          <i class="pi pi-plus text-xs text-color-secondary"></i>
          <span class="text-xs font-semibold w-2rem">{{ Math.round(zoom * 100) }}%</span>
        </div>

        <!-- Canvas for rendering cropped area (hidden) -->
        <canvas ref="canvasRef" width="320" height="480" class="hidden"></canvas>

        <!-- Actions -->
        <div class="flex justify-content-end gap-2 mt-2">
          <Button label="Annulla" severity="secondary" outlined size="small" @click="cancelEdit" :disabled="isUploading" />
          <Button label="Applica e Salva" icon="pi pi-check" severity="success" size="small" @click="applyCrop" :loading="isUploading" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.preview-container {
  width: 120px;
  height: 180px;
  background-color: var(--code-bg);
  border-color: var(--border);
  transition: border-color 0.3s;
}

.preview-container.compact-preview {
  width: 32px;
  height: 48px;
  border-width: 1px;
}

.preview-container:hover {
  border-color: var(--accent);
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cropper-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.6);
  z-index: 9999;
}

.cropper-card {
  max-width: 520px;
  width: 100%;
  background: var(--bg);
}

.crop-viewport {
  width: 100%;
  height: 340px; /* high viewport to contain the image and overlay */
  background-color: #111;
  user-select: none;
}

/* Image styling */
.crop-image-underlay {
  position: absolute;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  pointer-events: auto; /* allows drag events */
  transform-origin: center center;
  transition: transform 0.05s ease-out;
}

/* Dim overlay mask around the cropping box */
.crop-mask-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.55);
  pointer-events: none; /* let mouse click drag the image beneath */
  z-index: 10;
}

/* Bounding box corresponding to 2:3 ratio */
.crop-cutout-box {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 200px;  /* 200px width */
  height: 300px; /* 300px height (which is exactly 2:3 aspect ratio) */
  margin-left: -100px;
  margin-top: -150px;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.55); /* creates cutout effect */
  background: transparent;
  pointer-events: none;
  z-index: 20;
}

.zoom-slider {
  accent-color: var(--accent);
  cursor: pointer;
}

.position-relative {
  position: relative;
}

.text-xxs {
  font-size: 0.65rem;
}
</style>
