'use strict';
import {detectPhoto} from './detector.js';
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
let referenceMarks = [], heightEvidence = null;
let autoSession = 0;
const usingReference = () => $('heightSource').value === 'reference';
const ctx = $('canvas').getContext('2d');
$('uploadLabel').tabIndex = 0;
$('uploadLabel').setAttribute('role','button');
$('uploadLabel').onkeydown = event => {
  if ((event.key === 'Enter' || event.key === ' ') && !busy) { event.preventDefault(); $('photo').click(); }
};
function status(message, error = false) { $('status').textContent = message; $('status').classList.toggle('error', error); }
function heightInches() {
  const empty = $('unit').value === 'ft' ? !$('feet').value && !$('inches').value : !$('height').value;
  if (usingReference() && empty) return null;
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
function referenceLength() {
  const length = Number($('referenceType').value === 'custom' ? $('referenceLength').value : $('referenceType').value);
  if (!Number.isFinite(length) || length < 10 || length > 200) throw Error('Enter the actual vertical reference length, from 10 to 200 cm.');
  return length;
}
function captureSetup() { heightInches(); if (usingReference()) referenceLength(); }
function calibrationPrompt() {
  if (marks.length < 2) return marks.length ? 'Now mark the floor beneath your feet.' : 'Mark the top of your head, then the floor beneath your feet.';
  if (usingReference() && referenceMarks.length < 2) return referenceMarks.length ? 'Now mark the BOTTOM of the known vertical reference edge.' : 'Now mark the TOP of the known vertical reference edge.';
  return 'Check all marks, confirm reference placement if applicable, then generate estimates.';
}
function stopCamera() {
  autoSession++; $('viewfinder').classList.remove('scan-ready');
  if (countdown) { clearInterval(countdown); countdown = null; }
  if (stream) stream.getTracks().forEach(track => track.stop());
  stream = null; $('video').srcObject = null; $('video').hidden = true;
  $('snap').hidden = true; $('snap').disabled = false; $('snap').textContent = 'Capture in 5 seconds';
  $('stop').hidden = true; $('camera').hidden = false;
}
function lock(value) {
  busy = value;
  for (const id of ['camera','snap','photo','measure','retake','resetMarks','clear','unit','feet','inches','height','heightSource','referenceType','referenceLength','setupConfirmed','crown','floor','refTopX','refTopY','refBottomX','refBottomY']) $(id).disabled = value;
  $('uploadLabel').setAttribute('aria-disabled', String(value));
}
async function api(path, data) {
  const response = await fetch(path, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw Error(result.error || 'Request failed. Try again.');
  return result;
}
function invalidateResults() { estimates = null; measuredHeight = null; heightEvidence = null; $('heightReview').hidden = true; $('results').hidden = true; $('step3').classList.remove('active'); }
function clearCapture() {
  revision++; stopCamera(); photo = null; detection = null; marks = []; referenceMarks = []; $('setupConfirmed').checked = false;
  $('canvas').hidden = true; $('empty').hidden = false; $('calibration').hidden = true;
  $('photo').value = ''; invalidateResults(); $('step2').classList.remove('active');
  $('canvas').width = 1; $('canvas').height = 1;
}
$('heightSource').onchange = () => {
  $('referenceSetup').hidden = !usingReference(); $('referenceMarks').hidden = !usingReference();
  $('heightEntryLabel').textContent = usingReference() ? 'Optional measured height for cross-check' : 'Your measured height (required)';
  referenceMarks = []; $('setupConfirmed').checked = false; invalidateResults(); draw();
  status(usingReference() ? 'Include a known-length vertical reference beside your body. You can leave height blank.' : 'Enter a measured height. This mode cannot independently check your height.');
};
$('referenceType').onchange = () => { $('customReferenceField').hidden = $('referenceType').value !== 'custom'; $('setupConfirmed').checked=false; invalidateResults(); };
$('referenceLength').oninput = () => { $('setupConfirmed').checked=false; invalidateResults(); };
$('setupConfirmed').onchange = invalidateResults;
$('unit').onchange = () => {
  const unit = $('unit').value;
  $('feetFields').hidden = unit !== 'ft'; $('singleField').hidden = unit === 'ft';
  $('singleLabel').textContent = unit === 'cm' ? 'Centimetres' : 'Total inches';
  $('height').value = ''; $('height').placeholder = unit === 'cm' ? '172.7' : '68'; invalidateResults();
};
for (const id of ['feet','inches','height']) $(id).oninput = invalidateResults;
$('camera').onclick = async () => {
  try {
    captureSetup(); clearCapture(); lock(true);
    if (!navigator.mediaDevices?.getUserMedia) throw Error('Camera unavailable here. Open this app on localhost in Chrome or Edge, or choose a photo.');
    status('Requesting camera access…');
    stream = await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:960},facingMode:'user'},audio:false});
    $('video').srcObject = stream; await $('video').play();
    $('empty').hidden = true; $('video').hidden = false; $('camera').hidden = true;
    $('snap').hidden = true; $('stop').hidden = false; $('step2').classList.add('active');
    status('Step into position. I will wait until your full body is visible and steady.');
    monitorCamera(++autoSession);
  } catch (error) {
    stopCamera(); $('empty').hidden = false;
    const messages = {NotAllowedError:'Camera permission was denied. Allow camera access in your browser or choose a photo.',NotFoundError:'No camera found. Connect a webcam or choose a photo.',NotReadableError:'Camera is in use by another application. Close it or choose a photo.'};
    status(messages[error.name] || error.message, true);
  } finally { lock(false); }
};
$('stop').onclick = () => { stopCamera(); $('empty').hidden = false; status('Camera stopped. Start again or choose a photo.'); };
async function monitorCamera(session) {
  let previous = null, steadySince = null;
  const sample = document.createElement('canvas');
  while (stream && session === autoSession) {
    try {
      const video = $('video');
      if (!video.videoWidth) throw Error('Waiting for the camera…');
      const scale = Math.min(1,960/video.videoWidth);
      sample.width = Math.round(video.videoWidth*scale); sample.height = Math.round(video.videoHeight*scale);
      sample.getContext('2d').drawImage(video,0,0,sample.width,sample.height);
      const image = new Image(); image.src = sample.toDataURL('image/jpeg',0.9); await image.decode();
      const body = await detectPhoto(image);
      if (session !== autoSession || !stream) return;
      const indices = [0,11,12,23,24,25,26,27,28];
      const upright = body.points[11].y < body.points[23].y && body.points[23].y < body.points[25].y && body.points[25].y < body.points[27].y;
      if (!upright) throw Error('Stand upright facing the camera, with straight legs.');
      const movement = previous ? Math.max(...indices.map(i => Math.hypot(body.points[i].x-previous[i].x,body.points[i].y-previous[i].y))) : Infinity;
      previous = body.points;
      if (movement > 0.015) steadySince = null;
      else if (steadySince === null) steadySince = performance.now();
      const elapsed = steadySince === null ? 0 : performance.now()-steadySince;
      $('viewfinder').classList.toggle('scan-ready',elapsed>0);
      status(elapsed>0 ? `Good position. Hold still… ${Math.min(100,Math.round(elapsed/3500*100))}%` : 'Full body found. Stand still and face the camera.');
      if (elapsed >= 3500) {
        const source = image.src; stopCamera();
        await processPhoto(source);
        if (detection) status('Good job — steady full-body capture complete. Review the height calibration below to calculate measurements.');
        return;
      }
    } catch (error) {
      if (session !== autoSession) return;
      previous=null; steadySince=null; $('viewfinder').classList.remove('scan-ready');
      status(error.message);
      if (/Could not load|could not run/.test(error.message)) { stopCamera(); status(error.message,true); return; }
    }
    await new Promise(resolve=>setTimeout(resolve,500));
  }
}
$('photo').onchange = async event => {
  if (busy) return;
  const file = event.target.files[0]; if (!file) return;
  try {
    captureSetup();
    if (file.size > 12 * 1024 * 1024) throw Error('Choose a photo smaller than 12 MB.');
    if (!['image/jpeg','image/png','image/webp'].includes(file.type)) throw Error('Choose a JPEG, PNG or WebP photo.');
    stopCamera();
    const url = URL.createObjectURL(file);
    try { await processPhoto(url); } finally { URL.revokeObjectURL(url); }
  } catch (error) { status(error.message,true); }
  finally { $('photo').value = ''; }
};
async function processPhoto(source) {
  lock(true); invalidateResults(); detection = null; marks = []; referenceMarks = []; $('setupConfirmed').checked = false; $('calibration').hidden = true;
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
    const result = await detectPhoto(photo);
    if (current !== revision) return;
    detection = result; $('calibration').hidden = false; $('step2').classList.add('active');
    for (const [id,value] of Object.entries({refTopX:150,refTopY:400,refBottomX:150,refBottomY:550})) $(id).value=value;
    $('crown').value = 50; $('floor').value = 950; draw();
    status('Body detected. ' + calibrationPrompt());
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
  if (usingReference()) {
    ctx.strokeStyle = '#ffb65b'; ctx.fillStyle = '#ffb65b';
    referenceMarks.forEach((point,index) => { ctx.beginPath(); ctx.arc(point.x,point.y,Math.max(5,w/150),0,Math.PI*2); ctx.fill(); ctx.fillText(index ? 'REF BOTTOM' : 'REF TOP',point.x+10,point.y); });
    if (referenceMarks.length === 2) { ctx.beginPath(); ctx.moveTo(referenceMarks[0].x,referenceMarks[0].y); ctx.lineTo(referenceMarks[1].x,referenceMarks[1].y); ctx.stroke(); }
  }
}
$('canvas').onclick = event => {
  if (!detection || busy) return;
  const rect = $('canvas').getBoundingClientRect();
  const y = Math.max(0,Math.min($('canvas').height-1,(event.clientY-rect.top)*$('canvas').height/rect.height));
  const x = Math.max(0,Math.min($('canvas').width-1,(event.clientX-rect.left)*$('canvas').width/rect.width));
  if (marks.length < 2) {
    marks.push(y); $(marks.length === 1 ? 'crown' : 'floor').value = y/$('canvas').height*1000;
  } else if (usingReference() && referenceMarks.length < 2) {
    referenceMarks.push({x,y}); const prefix = referenceMarks.length === 1 ? 'refTop' : 'refBottom';
    $(prefix+'X').value = x/$('canvas').width*1000; $(prefix+'Y').value = y/$('canvas').height*1000;
  } else return;
  invalidateResults(); draw();
  status(calibrationPrompt());
};
for (const id of ['crown','floor']) $(id).oninput = () => { marks = [Number($('crown').value)/1000*$('canvas').height,Math.min($('canvas').height-1,Number($('floor').value)/1000*$('canvas').height)]; invalidateResults(); draw(); status('Calibration adjusted. Generate estimates when the lines enclose your full height.'); };
for (const id of ['refTopX','refTopY','refBottomX','refBottomY']) $(id).oninput = () => {
  referenceMarks = [{x:Number($('refTopX').value)/1000*$('canvas').width,y:Number($('refTopY').value)/1000*$('canvas').height}, {x:Number($('refBottomX').value)/1000*$('canvas').width,y:Number($('refBottomY').value)/1000*$('canvas').height}];
  invalidateResults(); draw(); status(calibrationPrompt());
};
$('resetMarks').onclick = () => { marks=[]; referenceMarks=[]; $('setupConfirmed').checked=false; invalidateResults(); draw(); status(calibrationPrompt()); };
$('retake').onclick = () => { clearCapture(); status('Ready for another camera capture or photo.'); };
$('measure').onclick = async () => {
  try {
    const height = heightInches();
    if (!detection || marks.length !== 2) throw Error('Mark both the top of your head and the floor first.');
    let reference = null;
    if (usingReference()) {
      if (referenceMarks.length !== 2) throw Error('Mark the TOP and BOTTOM of the reference object, or adjust its sliders.');
      if (!$('setupConfirmed').checked) throw Error('Confirm the reference placement and camera setup before calculating height.');
      reference = {top:referenceMarks[0],bottom:referenceMarks[1],length_cm:referenceLength(),setup_confirmed:true};
    }
    lock(true); status('Calculating calibrated landmark estimates…');
    const result = await api('/api/measure',{...detection,height_source:$('heightSource').value,height_inches:height,reference,crown:marks[0],floor:marks[1]});
    heightEvidence = result.height;
    $('heightReview').hidden = false;
    $('heightReview').textContent = `${usingReference() ? 'Reference-estimated' : 'Entered'} height: ${(result.height.inches*2.54).toFixed(1)} cm (${result.height.inches.toFixed(1)} in). Unverified. ${result.message || 'Perspective, posture and reference placement can still cause error.'}`;
    if (!result.estimates) { status(result.message,true); $('heightReview').scrollIntoView({behavior:'smooth',block:'center'}); return; }
    estimates = result.estimates; measuredHeight = result.height.inches; renderResults();
    $('results').hidden = false; $('step3').classList.add('active'); $('results').scrollIntoView({behavior:'smooth'});
    status('Your estimates are ready. Review the results and add any tape measurements below.');
  } catch (error) { status(error.message,true); }
  finally { lock(false); }
};
function renderResults() {
  const factor = $('displayUnit').value === 'cm' ? 2.54 : 1;
  const unit = $('displayUnit').value;
  $('heightSummary').textContent = `${heightEvidence?.source === 'reference' ? 'Reference-estimated' : 'Entered'} height: ${(measuredHeight*factor).toFixed(1)} ${unit}. ${heightEvidence?.source === 'reference' ? 'Independent of entered height; calibration accuracy is not yet validated.' : 'Not independently verified by the scan.'} Weight is not required. Not approved for garment production.`;
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
  const report = {schema_version:3,pipeline_version:'reference_v1',capture_geometry:{width:detection.width,height:detection.height,crown:marks[0],floor:marks[1]},created_at:new Date().toISOString(),units:'inches',entered_height:heightEvidence.entered_inches,height_used:measuredHeight,height_evidence:heightEvidence,production_ready:false,weight:{status:'not_measured',required:false},garment:$('garment').value,preferred_fit:$('fit').value,status:'unvalidated_landmark_estimates',calibration:heightEvidence.source === 'reference' ? 'known_vertical_reference' : 'user_entered_height',camera_estimates:estimates,manual_measurements:manual,requires_manual_measurement:Object.keys(manualLabels).filter(key => !(key in manual)),notes:['Body measurements and height are inches. Reference length is explicitly labelled in cm; reference coordinates are pixels.','Manual entries are user-supplied and unverified.','No perfect-scan or accuracy guarantee. Projected landmark lengths are not garment dimensions. Confirm with a tailor before production.']};
  const url = URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
  const link = document.createElement('a'); link.href=url; link.download=`suit-measurements-${new Date().toISOString().replace(/[:.]/g,'-')}.json`; link.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$('clear').onclick = () => { clearCapture(); manual={}; for (const id of ['feet','inches','height']) $(id).value=''; status('Session cleared. Your photo and measurements have been removed from this page.'); window.scrollTo({top:0,behavior:'smooth'}); };
window.addEventListener('pagehide',stopCamera);
