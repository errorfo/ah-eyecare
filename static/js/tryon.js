document.addEventListener("DOMContentLoaded", function () {
  const video = document.getElementById("video");
  const canvas = document.getElementById("overlay");

  if (!canvas) {
    console.error("Canvas element not found");
    return;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    console.error("Failed to get 2D context from canvas");
    return;
  }

  const thumbs = document.querySelectorAll(".frame-thumb");
  let glassesImg = new Image();
  let glassesImgLoaded = false;

  // Helper to set glasses image and track loading
  function setGlasses(src) {
    glassesImgLoaded = false;
    glassesImg = new Image();
    glassesImg.onload = () => {
      glassesImgLoaded = true;
      console.log("Glasses image loaded:", src);
    };
    glassesImg.onerror = () => {
      glassesImgLoaded = false;
      console.error("Failed to load glasses image:", src);
    };
    glassesImg.src = src;
  }

  // Set default frame if available
  if (thumbs.length > 0) {
  setGlasses(thumbs[0].dataset.frame);
} else {
  // Fallback test image URL to debug without admin uploads
  setGlasses('static/pics/glasses_PNG54292.png');
}

  thumbs.forEach((t) => {
    t.addEventListener("click", () => {
      thumbs.forEach((x) => x.classList.remove("selected"));
      t.classList.add("selected");
      setGlasses(t.dataset.frame);
    });
  });

  // Smoothing variables
  let smoothX = 0,
    smoothY = 0,
    smoothAngle = 0,
    smoothW = 0,
    smoothH = 0;
  const smoothFactor = 0.35;

  // Initialize MediaPipe FaceMesh
  const faceMesh = new FaceMesh({
    locateFile: (file) =>
      `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
  });

  faceMesh.setOptions({
    maxNumFaces: 1,
    refineLandmarks: true,
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });

  faceMesh.onResults((results) => {
    if (
      !video.videoWidth ||
      !video.videoHeight ||
      !canvas ||
      !results.multiFaceLandmarks?.length
    ) {
      // No face detected or video not ready
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }

    canvas.width = video.videoWidth;canvas.style.width = "100%";
canvas.style.height = "auto";
video.style.width = "100%";
video.style.height = "auto";


    canvas.height = video.videoHeight;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw flipped video frame (mirror effect)
    ctx.save();
    ctx.translate(-canvas.width, 0);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    ctx.restore();

    const lm = results.multiFaceLandmarks[0];

    // Landmarks for glasses positioning
    const leftFace = lm[234];
    const rightFace = lm[454];
    const nose = lm[168];

    const dx = rightFace.x - leftFace.x;
    const dy = rightFace.y - leftFace.y;
    const angle = Math.atan2(dy, dx);

    const faceWidth = Math.sqrt(dx * dx + dy * dy) * canvas.width;
    const marginFactor = 0.85;
const maxWidth = canvas.width * 0.6;
const tW = Math.min(faceWidth * marginFactor, maxWidth);

const aspectRatio = glassesImg.height / glassesImg.width || 0.5;
const tH = tW * aspectRatio;

// Mirror the X coordinate to match flipped video
const tX = canvas.width - (((leftFace.x + rightFace.x) / 2) * canvas.width);
const tY = nose.y * canvas.height + tH * 0.02;


    // Smooth transitions
    smoothX += (tX - smoothX) * smoothFactor;
    smoothY += (tY - smoothY) * smoothFactor;
    smoothAngle += (angle - smoothAngle) * smoothFactor;
    smoothW += (tW - smoothW) * smoothFactor;
    smoothH += (tH - smoothH) * smoothFactor;

    // Debug logs
    // Uncomment if you want to debug:
    // console.log('Face pos:', smoothX.toFixed(2), smoothY.toFixed(2), 'Size:', smoothW.toFixed(2), smoothH.toFixed(2), 'Angle:', smoothAngle.toFixed(2));
    // console.log('Glasses loaded:', glassesImgLoaded);

    // Draw glasses if image loaded and sizes valid
    if (glassesImgLoaded && smoothW > 0 && smoothH > 0) {
      ctx.save();
      ctx.scale(-1, 1);
      ctx.translate(-smoothX, smoothY);
      ctx.rotate(smoothAngle);
      ctx.drawImage(glassesImg, -smoothW / 2, -smoothH / 2, smoothW, smoothH);
      ctx.restore();
    }
  });

  if (!video) {
    console.error("Video element not found");
    return;
  }

  const camera = new Camera(video, {
    onFrame: async () => {
      await faceMesh.send({ image: video });
    },
    width: 640,
    height: 480,
  });

  navigator.mediaDevices
    .getUserMedia({ video: true })    
    .then((stream) => {
      video.srcObject = stream;
      video.onloadedmetadata = () => {
        video.play();
        camera.start();
      };
    })
    .catch((err) => {
      alert("Please allow camera access.");
      console.error(err);
    });
});