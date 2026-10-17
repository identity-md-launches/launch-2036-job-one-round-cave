// Transfer only the image tool's new motif; preserve ancestral pixels exactly.
const fs = require('node:fs');
const crypto = require('node:crypto');
const media = require('../line-1/media/finish-wall.cjs');
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const oldBytes = fs.readFileSync('artifacts/line-4/wall-v11.png');
const draftBytes = fs.readFileSync('artifacts/line-4/wall-v12.png');
const old = media.decode(oldBytes), draft = media.decode(draftBytes);
const record = JSON.parse(fs.readFileSync('dist/line-4/30.json', 'utf8'));
if (!record.image.endsWith(sha(oldBytes))) throw Error('ancestor hash mismatch');
const output = {...old, pixels: Buffer.from(old.pixels)};
const clamp = v => Math.max(0, Math.min(1, v));
function mask(x,y) {
  // On previously bare upper-center rock; no inherited mark enters this area.
  const left = clamp((49 - Math.hypot(x-568,y-322))/3);
  const right = clamp((29 - Math.hypot(x-701,y-336))/3);
  const cord = x >= 607 && x <= 678 ? clamp((12-Math.abs(y-(322+(x-607)*.12)))/3) : 0;
  return Math.max(left,right,cord);
}
let changed = 0, outside = 0;
for (let y=0;y<old.height;y++) for(let x=0;x<old.width;x++) {
  const a=mask(x,y), j=(y*old.width+x)*3;
  for(let c=0;c<3;c++) output.pixels[j+c]=Math.round(old.pixels[j+c]*(1-a)+draft.pixels[j+c]*a);
  const differs=!output.pixels.subarray(j,j+3).equals(old.pixels.subarray(j,j+3));
  if(differs) changed++;
  if(!a && differs) outside++;
}
if(changed<500 || outside) throw Error('mark/preservation failure');
const wall=media.encode(output), jpeg=media.thumbnail(output);
if(jpeg.length>100000 || !media.decode(wall).pixels.equals(output.pixels)) throw Error('encoding check failed');
fs.writeFileSync('artifacts/line-4/wall-v12.png',wall);
fs.writeFileSync('artifacts/line-4/wall.png',wall);
fs.writeFileSync('artifacts/line-4/31.jpg',jpeg);
fs.linkSync('artifacts/line-4/31.jpg','dist/line-4/31.jpg');
const report={ancestor_sha256:sha(oldBytes),generated_edit_sha256:sha(draftBytes),sha256:sha(wall),
  png_dimensions:[old.width,old.height],png_format:'RGB PNG',jpeg_dimensions:[512,512],jpeg_format:'JPEG',
  jpeg_bytes:jpeg.length,changed_pixels:changed,pixels_changed_outside_addition:outside,
  visual_review:'Two ochre tokens joined by a charcoal cord above Pepe. Existing marks and two five-digit hands preserved; no new hands, text or numbers.',
  unmet_visual_requirements:['Inherited photographic rock texture retained to preserve the wall.'],
  method:'Built-in image editor followed by restricted token/cord mask on ancestral pixels.'};
fs.writeFileSync('line-4/review-31.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
