'use strict';
const $ = id => document.getElementById(id);
const labels = {
  shoulder_landmark_span: 'Shoulder joint span',
  left_arm_landmark_length: 'Left arm · shoulder to wrist',
  right_arm_landmark_length: 'Right arm · shoulder to wrist',
  left_hip_to_ankle_landmark_length: 'Left leg · hip to ankle',
  right_hip_to_ankle_landmark_length: 'Right leg · hip to ankle'
};
const manualLabels = {chest_circumference:'Chest circumference', waist_circumference:'Waist circumference', hip_circumference:'Hip circumference', thigh_circumference:'Thigh circumference', inseam:'Inseam', outseam:'Outseam', garment_sleeve_length:'Garment sleeve length'};
let stream = null, photo = null, detection = null, marks = [], estimates = null;
let measuredHeight = null, manual = {}, revision = 0, busy = false, countdown = null;
const ctx = $('canvas').getContext('2d');
$('uploadLabel').tabIndex = 0;
$('uploadLabel').setAttribute('role','button');
$('uploadLabel').onkeydown = event => {
  if ((event.key === 'Enter' || event.key === ' ') && !busy) { event.preventDefault(); $('photo').click(); }
};
function status(message, error = false) { $('status').textContent = message; $('status').classList.toggle('error', error); }
function heightInches() {
  let value;
  if ($('unit').value === 'ft') {
    const feet = Number($('feet').value), inches = Number($('inches').value);
    if (!$('feet').value || !$('inches').value || !Number.isInteger(feet) || inches < 0 || inches >= 12) throw Error('Enter feet and inches, including 0 inches when applicable.');
    value = feet * 12 + inches;
  } else {
    if (!$('height').value) throw Error('Enter your measured height first.');
    value = Number($('height').value) / ($('unit').value === 'cm' ? 2.54 : 1);
  }
  if (!Number.isFinite(value) || value < 24 || value > 100) throw Error('Height must be between 24 and 100 inches (61–254 cm).');
  return value;
}
function stopCamera() {
  if (countdown) { clearInterval(countdown); countdown = null; }
  if (stream) stream.getTracks().forEach(track => track.stop());
  stream = null; $('video').srcObject = null; $('video').hidden = true;
  $('snap').hidden = true; $('snap').disabled = false; $('snap').textContent = 'Capture in 5 seconds';
  $('stop').hidden = true; $('camera').hidden = false;
}
function lock(value) {
  busy = value;
  for (const id of ['camera','snap','photo','measure','retake','resetMarks','clear','unit','feet','inches','height']) $(id).disabled = value;
  $('uploadLabel').setAttribute('aria-disabled', String(value));
}
async function api(path, data) {
  const response = await fetch(path, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw Error(result.error || 'Request failed. Try again.');
  return result;
}
function invalidateResults() { estimates = null; measuredHeight = null; $('results').hidden = true; $('step3').classList.remove('active'); }
function clearCapture() {
  revision++; stopCamera(); photo = null; detection = null; marks = [];
  $('canvas').hidden = true; $('empty').hidden = false; $('calibration').hidden = true;
  $('photo').value = ''; invalidateResults(); $('step2').classList.remove('active');
  $('canvas').width = 1; $('canvas').height = 1;
}
$('unit').onchange = () => {
  const unit = $('unit').value;
  $('feetFields').hidden = unit !== 'ft'; $('singleField').hidden = unit === 'ft';
  $('singleLabel').textContent = unit === 'cm' ? 'Centimetres' : 'Total inches';
  $('height').value = ''; $('height').placeholder = unit === 'cm' ? '172.7' : '68'; invalidateResults();
};
for (const id of ['feet','inches','height']) $(id).oninput = invalidateResults;
$('camera').onclick = async () => {
  try {
    heightInches(); clearCapture(); lock(true);
    if (!navigator.mediaDevices?.getUserMedia) throw Error('Camera unavailable here. Open this app on localhost in Chrome or Edge, or choose a photo.');
    status('Requesting camera access…');
    stream = await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:960},facingMode:'user'},audio:false});
    $('video').srcObject = stream; await $('video').play();
    $('empty').hidden = true; $('video').hidden = false; $('camera').hidden = true;
    $('snap').hidden = false; $('stop').hidden = false; $('step2').classList.add('active');
    status('Camera ready. Stand back until your full body fits. Capture gives you 5 seconds to get into position.');
  } catch (error) {
    stopCamera(); $('empty').hidden = false;
    const messages = {NotAllowedError:'Camera permission was denied. Allow camera access in your browser or choose a photo.',NotFoundError:'No camera found. Connect a webcam or choose a photo.',NotReadableError:'Camera is in use by another application. Close it or choose a photo.'};
    status(messages[error.name] || error.message, true);
  } finally { lock(false); }
};
$('stop').onclick = () => { stopCamera(); $('empty').hidden = false; status('Camera stopped. Start again or choose a photo.'); };
$('snap').onclick = () => {
  if (!stream || countdown || busy) return;
  let remaining = 5; $('snap').disabled = true;
  status(`Capturing in ${remaining}… Stand straight and keep both feet visible.`);
  countdown = setInterval(() => {
    remaining--;
    if (remaining > 0) return status(`Capturing in ${remaining}…`);
    clearInterval(countdown); countdown = null;
    const video = $('video');
    if (!video.videoWidth || !video.videoHeight) { stopCamera(); return status('Camera has no image. Please try again.', true); }
    const temporary = document.createElement('canvas'); temporary.width = video.videoWidth; temporary.height = video.videoHeight;
    temporary.getContext('2d').drawImage(video,0,0);
    stopCamera(); processPhoto(temporary.toDataURL('image/jpeg',0.92));
  },1000);
};
$('photo').onchange = async event => {
  if (busy) return;
  const file = event.target.files[0]; if (!file) return;
  try {
    heightInches();
    if (file.size > 12 * 1024 * 1024) throw Error('Choose a photo smaller than 12 MB.');
    if (!['image/jpeg','image/png','image/webp'].includes(file.type)) throw Error('Choose a JPEG, PNG or WebP photo.');
    stopCamera();
    const url = URL.createObjectURL(file);
    try { await processPhoto(url); } finally { URL.revokeObjectURL(url); }
  } catch (error) { status(error.message,true); }
  finally { $('photo').value = ''; }
};
async function processPhoto(source) {
  lock(true); invalidateResults(); detection = null; marks = []; $('calibration').hidden = true;
  const current = ++revision;
  try {
    status('Checking full-body visibility… The first capture may take a moment.');
    const image = new Image(); image.src = source; await image.decode();
    if (image.naturalWidth * image.naturalHeight > 40_000_000) throw Error('Photo too large. Please resize it below 40 megapixels.');
    const scale = Math.min(1,1600 / Math.max(image.naturalWidth,image.naturalHeight));
    const canvas = $('canvas'); canvas.width = Math.round(image.naturalWidth * scale); canvas.height = Math.round(image.naturalHeight * scale);
    ctx.drawImage(image,0,0,canvas.width,canvas.height);
    photo = new Image(); photo.src = canvas.toDataURL('image/jpeg',0.92); await photo.decode();
    canvas.hidden = false; $('empty').hidden = true; $('video').hidden = true;
    const result = await api('/api/detect',{image:photo.src.split(',')[1]});
    if (current !== revision) return;
    detection = result; $('calibration').hidden = false; $('step2').classList.add('active');
    $('crown').value = 50; $('floor').value = 950; draw();
    status('Body detected. Click the top of your head, then the floor beneath your feet.');
  } catch (error) { status(error.message,true); }
  finally { lock(false); }
}
const connections = [[11,12],[11,13],[13,15],[12,14],[14,16],[11,23],[12,24],[23,24],[23,25],[25,27],[24,26],[26,28]];
function draw() {
  if (!photo) return;
  const canvas = $('canvas'); ctx.drawImage(photo,0,0);
  const w = canvas.width, h = canvas.height; ctx.lineWidth = Math.max(2,w/500); ctx.strokeStyle = '#bdeaaa';
  if (detection) {
    for (const [a,b] of connections) { ctx.beginPath(); ctx.moveTo(detection.points[a].x*w,detection.points[a].y*h); ctx.lineTo(detection.points[b].x*w,detection.points[b].y*h); ctx.stroke(); }
    for (const p of detection.points) { ctx.beginPath(); ctx.arc(p.x*w,p.y*h,Math.max(3,w/300),0,Math.PI*2); ctx.fillStyle = '#d7f3c1'; ctx.fill(); }
  }
  marks.forEach((y,index) => { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(w,y); ctx.strokeStyle = '#c9ff9c'; ctx.stroke(); ctx.font = `${Math.max(14,w/55)}px Arial`; ctx.fillStyle = '#c9ff9c'; ctx.fillText(index === 0 ? 'TOP OF HEAD' : 'FLOOR',10,Math.max(18,y-8)); });
}
$('canvas').onclick = event => {
  if (!detection || busy || marks.length >= 2) return;
  const rect = $('canvas').getBoundingClientRect();
  marks.push(Math.max(0,Math.min($('canvas').height-1,(event.clientY-rect.top)*$('canvas').height/rect.height)));
  $(marks.length === 1 ? 'crown' : 'floor').value = marks[marks.length-1]/$('canvas').height*1000;
  invalidateResults(); draw();
  status(marks.length === 1 ? 'Now click the floor beneath your feet.' : 'Check the two lines, then generate estimates.');
};
for (const id of ['crown','floor']) $(id).oninput = () => { marks = [Number($('crown').value)/1000*$('canvas').height,Math.min($('canvas').height-1,Number($('floor').value)/1000*$('canvas').height)]; invalidateResults(); draw(); status('Calibration adjusted. Generate estimates when the lines enclose your full height.'); };
$('resetMarks').onclick = () => { marks=[]; invalidateResults(); draw(); status('Click the top of your head, then the floor beneath your feet.'); };
$('retake').onclick = () => { clearCapture(); status('Ready for another camera capture or photo.'); };
$('measure').onclick = async () => {
  try {
    const height = heightInches();
    if (!detection || marks.length !== 2) throw Error('Mark both the top of your head and the floor first.');
    lock(true); status('Calculating calibrated landmark estimates…');
    const result = await api('/api/measure',{...detection,height_inches:height,crown:marks[0],floor:marks[1]});
    estimates = result.estimates; measuredHeight = height; renderResults();
    $('results').hidden = false; $('step3').classList.add('active'); $('results').scrollIntoView({behavior:'smooth'});
    status('Your estimates are ready. Review the results and add any tape measurements below.');
  } catch (error) { status(error.message,true); }
  finally { lock(false); }
};
function renderResults() {
  const factor = $('displayUnit').value === 'cm' ? 2.54 : 1;
  const unit = $('displayUnit').value;
  $('estimateGrid').replaceChildren();
  for (const [key,value] of Object.entries(estimates || {})) {
    const card = document.createElement('div'); card.className = 'estimate';
    const label = document.createElement('span'); label.textContent = labels[key];
    const amount = document.createElement('strong'); amount.textContent = `${(value*factor).toFixed(1)} ${unit}`;
    const badge = document.createElement('small'); badge.textContent = 'CAMERA ESTIMATE · UNVALIDATED';
    card.append(label,amount,badge); $('estimateGrid').append(card);
  }
  $('manualGrid').replaceChildren();
  for (const [key,label] of Object.entries(manualLabels)) {
    const wrapper = document.createElement('label'); wrapper.textContent = `${label} (${unit})`;
    const input = document.createElement('input'); input.type = 'number'; input.min = '0.1'; input.max = String(150*factor); input.step = '0.1'; input.placeholder = 'Not measured';
    input.value = manual[key] ? (manual[key]*factor).toFixed(1) : '';
    input.oninput = () => {
      const value = Number(input.value)/factor;
      if (input.value && (!Number.isFinite(value) || value <= 0 || value > 150)) { input.setCustomValidity('Enter a positive measurement up to 150 inches (381 cm).'); delete manual[key]; }
      else { input.setCustomValidity(''); if (input.value) manual[key]=value; else delete manual[key]; }
    };
    wrapper.append(input); $('manualGrid').append(wrapper);
  }
}
$('displayUnit').onchange = renderResults;
$('download').onclick = () => {
  for (const input of $('manualGrid').querySelectorAll('input')) if (!input.reportValidity()) return;
  if (!estimates) return;
  const report = {schema_version:2,created_at:new Date().toISOString(),units:'inches',entered_height:measuredHeight,garment:$('garment').value,preferred_fit:$('fit').value,status:'unvalidated_landmark_estimates',calibration:'user_marked_crown_and_floor',camera_estimates:estimates,manual_measurements:manual,requires_manual_measurement:Object.keys(manualLabels).filter(key => !(key in manual)),notes:['All exported values are inches.','Manual entries are user-supplied and unverified.','Projected landmark lengths are not garment dimensions. Confirm with a tailor before production.']};
  const url = URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
  const link = document.createElement('a'); link.href=url; link.download=`suit-measurements-${new Date().toISOString().replace(/[:.]/g,'-')}.json`; link.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$('clear').onclick = () => { clearCapture(); manual={}; for (const id of ['feet','inches','height']) $(id).value=''; status('Session cleared. Your photo and measurements have been removed from this page.'); window.scrollTo({top:0,behavior:'smooth'}); };
window.addEventListener('pagehide',stopCamera);
