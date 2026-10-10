import {useEffect,useRef} from 'react';
import * as T from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';
import {mergeGeometries} from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import {createExplosionLayout} from './explosion-layout';
import {decodeModelResponse} from './model-download';
import {PointerTap} from './pointer-tap';
import {SYSTEMS,variantShown,type Atlas,type SceneState} from './anatomy';
import {REGION_KIND,membership,regionGeometry,regionOfPart,type RegionId} from './regions';
import {JOINTS} from './motion';
interface Props {quality?:'hi'|'lo';atlas:Atlas;state:SceneState;onSelect:(id:string)=>void;onProgress:(n:number)=>void;onError:(s:string)=>void;onMotion?:(progress:number)=>void}
export default function AnatomyScene({quality='hi',atlas,state,onSelect,onProgress,onError,onMotion}:Props){
 const host=useRef<HTMLDivElement>(null),latest=useRef(state),select=useRef(onSelect),motionCb=useRef(onMotion);
 latest.current=state;select.current=onSelect;motionCb.current=onMotion;
 useEffect(()=>{
  const el=host.current!;let disposed=false,frame=0,dirty=true,ready=false,lastView='',lastReset=-1,lastIsolate='',layoutKey='',amount=0;
  let lastState:SceneState|null=null;
  const abort=new AbortController();
  let renderer:T.WebGLRenderer;
  try{renderer=new T.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});}catch{onError('Браузер не смог запустить 3D. Попробуйте браузер с поддержкой WebGL.');return;}
  renderer.setPixelRatio(Math.min(devicePixelRatio,innerWidth<768?1.5:2));renderer.setClearColor('#f2f3f3');renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.12;el.appendChild(renderer.domElement);
  renderer.domElement.setAttribute('aria-label','Интерактивная анатомия человека. Тяните, чтобы вращать, щипком или колесом меняйте масштаб, нажмите на структуру, чтобы рассмотреть её.');
  const scene=new T.Scene(),camera=new T.PerspectiveCamera(34,1,.005,100),controls=new OrbitControls(camera,renderer.domElement);
  camera.position.set(1.4,1.05,3.6);controls.target.set(0,.85,0);controls.enableDamping=true;controls.dampingFactor=.085;controls.minDistance=.07;controls.maxDistance=40;controls.maxPolarAngle=Math.PI*.96;controls.addEventListener('change',()=>{dirty=true;});
  const pmrem=new T.PMREMGenerator(renderer),room=new RoomEnvironment(),env=pmrem.fromScene(room,.04);scene.environment=env.texture;room.dispose();pmrem.dispose();
  scene.add(new T.HemisphereLight(0xffffff,0xa7acb2,1.05));
  const key=new T.DirectionalLight(0xfffaf4,2.3);key.position.set(-2,4,3);scene.add(key);
  const rim=new T.DirectionalLight(0xe9f0ff,1.8);rim.position.set(2,2,-3);scene.add(rim);
  const ground=new T.Mesh(new T.CircleGeometry(30,96),new T.MeshStandardMaterial({color:0xd5d9dc,roughness:1}));ground.rotation.x=-Math.PI/2;ground.position.y=-.019;scene.add(ground);
  const platform=new T.Mesh(new T.CylinderGeometry(.68,.7,.028,100),new T.MeshStandardMaterial({color:0xeeeeec,metalness:.12,roughness:.67}));platform.position.y=-.016;scene.add(platform);
  const ring=new T.Mesh(new T.RingGeometry(.63,.632,128),new T.MeshBasicMaterial({color:0x8c969f,transparent:true,opacity:.4,side:T.DoubleSide}));ring.rotation.x=-Math.PI/2;ring.position.y=.001;scene.add(ring);
  const innerRing=new T.Mesh(new T.RingGeometry(.55,.551,128),new T.MeshBasicMaterial({color:0xa4aeb8,transparent:true,opacity:.16,side:T.DoubleSide}));innerRing.rotation.x=-Math.PI/2;innerRing.position.y=.001;scene.add(innerRing);
  const width=T.MathUtils.ceilPowerOfTwo(atlas.parts.length),data=new Float32Array(width*4),partTexture=new T.DataTexture(data,width,1,T.RGBAFormat,T.FloatType);partTexture.needsUpdate=true;
  const selectedData=new Uint8Array(width*4),selectionTexture=new T.DataTexture(selectedData,width,1);selectionTexture.needsUpdate=true;
  const materials:T.Material[]=[],geometries:T.BufferGeometry[]=[],pickers:(T.Mesh|undefined)[]=[],centers=atlas.parts.map(p=>new T.Vector3().fromArray(p.bounds[0]).add(new T.Vector3().fromArray(p.bounds[1])).multiplyScalar(.5));
  const offsets:T.Vector3[]=[],bounds=atlas.parts.map(p=>new T.Box3(new T.Vector3().fromArray(p.bounds[0]),new T.Vector3().fromArray(p.bounds[1])));
  let packingWidth=1,packingHeight=1;
  const markerPositions=new Float32Array(atlas.parts.length*3),markerGeometry=new T.BufferGeometry();markerGeometry.setAttribute('position',new T.BufferAttribute(markerPositions,3));
  const markerMaterial=new T.PointsMaterial({color:0x64748b,size:5,sizeAttenuation:false,transparent:true,opacity:.72,depthTest:false});
  markerMaterial.onBeforeCompile=shader=>{shader.fragmentShader=shader.fragmentShader.replace('#include <clipping_planes_fragment>','#include <clipping_planes_fragment>\nif (distance(gl_PointCoord, vec2(0.5)) > 0.5) discard;');};
  const markers=new T.Points(markerGeometry,markerMaterial);markers.frustumCulled=false;markers.renderOrder=10;markers.visible=false;scene.add(markers);
  const labelLayer=document.createElement('div');labelLayer.className='scene-labels';el.appendChild(labelLayer);const labelPool:HTMLButtonElement[]=[];
  const baseName=(n:string)=>n.replace(/ \((лев|прав)\.\)$/,'');
  const volume=(i:number)=>{const b=atlas.parts[i].bounds;return (b[1][0]-b[0][0])*(b[1][1]-b[0][1])*(b[1][2]-b[0][2]);};
  const muscleRich=atlas.parts.filter(p=>p.system==='muscular').length>100;
  const DEEP=/diaphragm|intercostal|psoas|iliacus|transversus|rotator|interspinal|intertransvers|levatores|obturator|gemellus|quadratus femoris|piriformis|coccygeus|iliococcyg|pubococc|puborect|subscapularis|serratus posterior|semispinalis|longissimus|iliocostalis|spinalis|splenius|rectus capitis|obliquus capitis|longus colli|longus capitis|scalenus|pectoralis minor|profundus|vastus intermedius|adductor (brevis|magnus|minimus)|tibialis posterior|flexor (hallucis|digitorum) longus|popliteus|brachialis$|supinator|pronator quadratus|extensor indicis|of foot|lumbrical|interosse|pharyngeal|palat|crico|arytenoid|vocalis|glossus|mylohyoid|geniohyoid|stylohyoid|papillary|sphincter|perineal|uvular|gluteus minimus|teres minor|coracobrachialis|anconeus|plantaris|(superior|inferior|medial|lateral) rectus$|(superior|inferior) oblique$|levator palpebrae/i;
  const labelCandidates=new Map<string,number[]>();{const seen=new Set<string>();atlas.parts.map((_,i)=>i).sort((a,b)=>volume(b)-volume(a)).forEach(i=>{const p=atlas.parts[i],k=p.system+':'+baseName(p.name);if(seen.has(k)||p.system==='hair'||(p.system==='muscular'&&DEEP.test(p.en??'')))return;seen.add(k);const l=labelCandidates.get(p.system)??[];if(l.length<40)l.push(i);labelCandidates.set(p.system,l);});}
  const drawLabels=(s:SceneState)=>{
   const show=!!s.labels&&amount<.05&&ready;let used=0;
   if(show){const w=el.clientWidth,h=el.clientHeight,max=w<768?8:14,rects:number[][]=[];const ORG=['respiratory','digestive','cardiac','urinary','reproductive','endocrine','lymphatic'];const vis=s.visible;const sys=s.isolate?[]:vis.includes('muscular')&&muscleRich?['muscular']:vis.includes('skeletal')?vis.filter(x=>x==='skeletal'||ORG.includes(x)):vis.filter(x=>x!=='skin'||vis.length===1);const lists=sys.map(x=>labelCandidates.get(x)??[]);const pick:number[]=[];for(let r=0;r<40&&pick.length<max*3;r++)for(const l of lists)if(l[r]!==undefined)pick.push(l[r]);if(s.isolate)pick.push(...atlas.parts.map((p,i)=>s.selected.includes(p.id)?i:-1).filter(i=>i>=0));
    for(const i of pick){if(used>=max)break;const a=anchors[i];if(!a||data[i*4+3]<.5)continue;projected.set(a.x+data[i*4],a.y+data[i*4+1],a.z+data[i*4+2]).project(camera);if(projected.z>1||Math.abs(projected.x)>1||Math.abs(projected.y)>1)continue;if(clipPlane.distanceToPoint(new T.Vector3(a.x+data[i*4],a.y+data[i*4+1],a.z+data[i*4+2]))<0)continue;const x=(projected.x+1)/2*w,y=(1-projected.y)/2*h,name=baseName(atlas.parts[i].name),tw=Math.min(180,name.length*6.6+22);let left=x+6,top=y-10;if(left+tw>w-8)left=x-6-tw;const r=[left,top,left+tw,top+20];if(top<70||top>h-150||rects.some(q=>r[0]<q[2]&&r[2]>q[0]&&r[1]<q[3]&&r[3]>q[1]))continue;rects.push(r);
     let b=labelPool[used];if(!b){b=document.createElement('button');b.type='button';b.className='scene-label';b.addEventListener('click',()=>{const id=b!.dataset.id;if(id)select.current(id);});labelLayer.appendChild(b);labelPool.push(b);}
     b.dataset.id=atlas.parts[i].id;b.textContent=name;b.style.transform=`translate(${Math.round(left)}px,${Math.round(top)}px)`;b.classList.toggle('flip',left<x);b.style.setProperty('--dot',`${Math.round(left<x?tw:0)}px`);b.hidden=false;used++;}}
   for(let k=used;k<labelPool.length;k++)labelPool[k].hidden=true;
  };
  const hover=document.createElement('div');hover.className='part-hover';hover.setAttribute('role','tooltip');hover.hidden=true;el.appendChild(hover);
  type Target={index:number;x:number;y:number;left:number;right:number;top:number;bottom:number};let targets:Target[]=[];
  const projected=new T.Vector3();
  const findTarget=(x:number,y:number,radius:number)=>{
   let best=-1,score=Infinity;
   for(const t of targets){const dx=Math.max(t.left-x,0,x-t.right),dy=Math.max(t.top-y,0,y-t.bottom),distance=Math.hypot(dx,dy);if(distance>radius)continue;const candidate=distance+Math.hypot(t.x-x,t.y-y)*.025;if(candidate<score){score=candidate;best=t.index;}}
   return best;
  };
  const clipPlane=new T.Plane(new T.Vector3(0,-1,0),1000);renderer.localClippingEnabled=true;let clipKey='';
  // Изоляция области и демонстрация движения: общие таблицы границ областей и параметры сустава.
  const RG=regionGeometry(atlas);
  const U={regKind:{value:0},regSide:{value:0},motKind:{value:0},motSide:{value:0},armY:{value:RG.armY},armX:{value:RG.armX},regLim:{value:new T.Vector4(RG.armMinY,RG.armMaxY,RG.legC0,RG.legC1)},regHead:{value:new T.Vector2(RG.headY,RG.headX)},
   mOn:{value:0},mPivot:{value:new T.Vector3()},mAxis:{value:new T.Vector3(1,0,0)},mAngle:{value:0},mD:{value:new T.Vector3(0,-1,0)},mB:{value:.03},mTwist:{value:0},mO:{value:new T.Vector3()},mI:{value:new T.Vector3()},mBulge:{value:0}};
  const GLSL_REGION=`uniform float regKind; uniform float regSide; uniform float motKind; uniform float motSide; uniform float armY[8]; uniform float armX[8]; uniform vec4 regLim; uniform vec2 regHead;
float armTable(float y){ if(y<=armY[0]) return armX[0]; for(int k=1;k<8;k++){ if(y<=armY[k]){ float t=(y-armY[k-1])/(armY[k]-armY[k-1]); return mix(armX[k-1],armX[k],t);} } return armX[7]; }
float sst(float a,float b,float x){ return smoothstep(a,b,x); }
float armM(vec3 p,float s){ const float m=0.012; return sst(-m,m,s*p.x-armTable(p.y))*sst(regLim.x-m,regLim.x+m,p.y)*(1.0-sst(regLim.y-m,regLim.y+m,p.y)); }
float legM(vec3 p,float s){ const float m=0.012; return sst(-m,m,regLim.z+regLim.w*abs(p.x)-p.y)*sst(-m,m,s*p.x)*(1.0-armM(p,s)); }
float headM(vec3 p){ const float m=0.012; return sst(-m,m,p.y-regHead.x)*sst(-m,m,regHead.y-abs(p.x)); }
float regionM(vec3 p,float kind,float side){ if(kind<0.5) return 1.0; if(kind<1.5) return armM(p,side); if(kind<2.5) return legM(p,side); if(kind<3.5) return headM(p); return max(0.0,1.0-armM(p,1.0)-armM(p,-1.0)-legM(p,1.0)-legM(p,-1.0)-headM(p)); }
`;
  const GLSL_MOTION=`uniform float mOn; uniform vec3 mPivot; uniform vec3 mAxis; uniform float mAngle; uniform vec3 mD; uniform float mB; uniform float mTwist; uniform vec3 mO; uniform vec3 mI; uniform float mBulge;
vec3 rotA(vec3 v,vec3 k,float a){ float c=cos(a),s=sin(a); return v*c+cross(k,v)*s+k*dot(k,v)*(1.0-c); }
float motionW(vec3 rest,float mode){ if(mode<1.5) return 1.0; float s=dot(rest-mPivot,mD); float w=mTwist>0.5?clamp(s/mB,0.0,1.0):smoothstep(-mB,mB,s); return w*regionM(rest,motKind,motSide); }
`;
  const materialFor=(system:string)=>{
   const m=new T.MeshStandardMaterial({color:SYSTEMS.find(s=>s.id===system)?.color??'#aebbb8',metalness:.08,roughness:.53,side:T.DoubleSide,transparent:system==='skin',opacity:system==='skin'?.42:1,depthWrite:system!=='skin'});m.clippingPlanes=[clipPlane];
   m.onBeforeCompile=shader=>{
    shader.uniforms.partState={value:partTexture};shader.uniforms.selectionState={value:selectionTexture};shader.uniforms.stateWidth={value:width};Object.assign(shader.uniforms,U);
    shader.vertexShader='attribute float partIndex; uniform sampler2D partState; uniform sampler2D selectionState; uniform float stateWidth; varying float partVisible; varying float partSelected; varying float partClip; varying float partMode; varying vec3 restPos;\n'+GLSL_REGION+GLSL_MOTION+shader.vertexShader;
    shader.vertexShader=shader.vertexShader.replace('#include <beginnormal_vertex>','#include <beginnormal_vertex>\nvec4 selState = texture2D(selectionState, vec2((partIndex + 0.5) / stateWidth, 0.5)); float mMode = floor(selState.g * 255.0 / 60.0 + 0.5); float mW = (mOn > 0.5 && mMode > 0.5) ? motionW(position, mMode) : 0.0; if (mW > 0.0) objectNormal = rotA(objectNormal, mAxis, mAngle * mW);');
    shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvec2 stateUv = vec2((partIndex + 0.5) / stateWidth, 0.5); vec4 state = texture2D(partState, stateUv); restPos = position; partMode = mMode; if (mW > 0.0 || (mOn > 0.5 && mMode > 2.5)) { vec3 p = transformed; if (mMode > 2.5) { vec3 ax = mI - mO; float t = clamp(dot(p - mO, ax) / max(dot(ax, ax), 1e-6), 0.0, 1.0); vec3 cc = mO + ax * t; p += (p - cc) * mBulge * sin(3.14159 * t); } transformed = rotA(p - mPivot, mAxis, mAngle * mW) + mPivot; } transformed += state.xyz; partVisible = state.w; partSelected = selState.r; partClip = selState.b;');
    shader.fragmentShader='varying float partVisible; varying float partSelected; varying float partClip; varying float partMode; varying vec3 restPos;\n'+GLSL_REGION+shader.fragmentShader;
    shader.fragmentShader=shader.fragmentShader.replace('#include <clipping_planes_fragment>','#include <clipping_planes_fragment>\nif (partVisible < 0.5) discard;\nif (partClip > 0.5 && regionM(restPos, regKind, regSide) < 0.5) discard;');
    shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>','#include <color_fragment>\ndiffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.42, 0.85, 0.78), partSelected * 0.75);\nif (partMode > 2.5) diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.86, 0.33, 0.27), 0.55);');
   };materials.push(m);return m;
  };
  const mats=new Map(SYSTEMS.map(s=>[s.id,materialFor(s.id)]));
  let loaded=0;const CH=quality==='lo'&&atlas.lowChunks?atlas.lowChunks:atlas.chunks;const anchors:(T.Vector3|undefined)[]=[];
  const loadChunk=async(ci:number)=>{
   const chunk=CH[ci],compressed=!!chunk.gzip&&typeof DecompressionStream!=='undefined';const response=await fetch(compressed?chunk.gzip!:chunk.url,{signal:abort.signal});const buffer=await decodeModelResponse(response,chunk.bytes,compressed);if(disposed)return;
   const groups=new Map<string,T.BufferGeometry[]>();
   atlas.parts.forEach((p,i)=>{
    const L=quality==='lo'&&p.lo?p.lo:null;if((L?L[0]:p.chunk)!==ci)return;
    const vc=L?L[5]:p.vertexCount,ic=L?L[6]:p.indexCount,pev=L?L[1]:p.ev!,pei=L?L[3]:p.ei!,pq=L?[L[7],L[8],L[9],L[10]]:p.q;
    const g=new T.BufferGeometry();
    if(atlas.codec==='vq1'&&pq){
     // Сжатая геометрия: квантованные позиции (дельта + varint) и индексы (high-watermark + varint); нормали считаем на месте.
     const bytes=new Uint8Array(buffer),pos=new Float32Array(vc*3),[lx,ly,lz,ext]=pq,k=ext/65535,lo=[lx,ly,lz];
     let o=pev;
     for(let c=0;c<3;c++){let acc=0;for(let v=0;v<vc;v++){let x=0,sh=0,b;do{b=bytes[o++];x+=(b&127)*2**sh;sh+=7;}while(b&128);acc+=(x%2?-(x+1)/2:x/2);pos[v*3+c]=acc*k+lo[c];}}
     const idx=new Uint32Array(ic);o=pei;let hw=0;
     for(let n=0;n<ic;n++){let x=0,sh=0,b;do{b=bytes[o++];x+=(b&127)*2**sh;sh+=7;}while(b&128);const val=hw-x;idx[n]=val;if(val===hw)hw++;}
     g.setAttribute('position',new T.BufferAttribute(pos,3));g.setIndex(new T.BufferAttribute(idx,1));g.computeVertexNormals();
     // точка для подписи: вершина, ближайшая к центру масс детали
     let mx=0,my=0,mz=0;for(let v=0;v<vc;v++){mx+=pos[v*3];my+=pos[v*3+1];mz+=pos[v*3+2];}mx/=vc;my/=vc;mz/=vc;let bi=0,bd=Infinity;for(let v=0;v<vc;v++){const d=(pos[v*3]-mx)**2+(pos[v*3+1]-my)**2+(pos[v*3+2]-mz)**2;if(d<bd){bd=d;bi=v;}}anchors[i]=new T.Vector3(pos[bi*3],pos[bi*3+1],pos[bi*3+2]);
    }else{
     g.setAttribute('position',new T.BufferAttribute(new Float32Array(buffer,p.positions,p.vertexCount*3),3));
     g.setAttribute('normal',new T.BufferAttribute(new Int16Array(buffer,p.normals,p.vertexCount*3),3,true));g.setIndex(new T.BufferAttribute(new Uint32Array(buffer,p.indices,p.indexCount),1));
    }
    g.boundingBox=bounds[i].clone();g.computeBoundingSphere();const pick=new T.Mesh(g);pick.matrixAutoUpdate=false;pickers[i]=pick;geometries.push(g);
    g.setAttribute('partIndex',new T.BufferAttribute(new Float32Array(g.attributes.position.count).fill(i),1));
    const list=groups.get(p.system)??[];list.push(g);groups.set(p.system,list);
   });
   groups.forEach((gs,system)=>{const geometry=mergeGeometries(gs,false);if(!geometry)throw new Error('Не удалось собрать 3D-модель.');geometries.push(geometry);const mesh=new T.Mesh(geometry,mats.get(system as never));mesh.frustumCulled=false;scene.add(mesh);});
   lastState=null;loaded++;onProgress(Math.round(loaded/CH.length*100));dirty=true;
  };
  (async()=>{try{let cursor=0;await Promise.all(Array.from({length:3},async()=>{while(cursor<CH.length){const i=cursor++;await loadChunk(i);}}));if(!disposed){ready=true;dirty=true;}}catch(e){if(!disposed)onError(e instanceof Error?e.message:'Не удалось загрузить анатомию.');}})();
  const fit=(view:string,extent=0)=>{
   const aspect=camera.aspect,mobile=el.clientWidth<768,normalDistance=mobile?Math.max(4.5,1.8*el.clientHeight/Math.max(160,el.clientHeight-350)/(2*Math.tan(T.MathUtils.degToRad(camera.fov/2)))):4;
   const reservedHeight=mobile?350:270;const availableAspect=Math.max(.35,(el.clientWidth-(mobile?40:340))/Math.max(160,el.clientHeight-reservedHeight));const atlasDistance=Math.max(packingHeight,packingWidth/availableAspect)/(2*Math.tan(T.MathUtils.degToRad(camera.fov/2)))*(el.clientHeight/Math.max(160,el.clientHeight-reservedHeight))*1.08;
   const distance=T.MathUtils.lerp(normalDistance,Math.max(.2,atlasDistance),extent);if(extent>.8)view='front';
   const direction=view==='front'?new T.Vector3(0,.02,1):view==='back'?new T.Vector3(0,.02,-1):view==='side'?new T.Vector3(1,.02,0):new T.Vector3(.35,.06,1).normalize();
   controls.target.set(extent>.1&&el.clientWidth>767?-packingWidth*.12:0,extent>.1||mobile?.85:.68,0);camera.position.copy(controls.target).addScaledVector(direction,distance);controls.update();dirty=true;
  };
  const resize=()=>{layoutKey='';lastState=null;renderer.setPixelRatio(Math.min(devicePixelRatio,el.clientWidth<768||el.clientHeight<600?1.5:2));camera.aspect=el.clientWidth/el.clientHeight;camera.updateProjectionMatrix();renderer.setSize(el.clientWidth,el.clientHeight);fit(latest.current.view,amount);};const observer=new ResizeObserver(resize);observer.observe(el);
  const raycaster=new T.Raycaster(),pointer=new T.Vector2(),tap=new PointerTap(),worldBox=new T.Box3(),hitPoint=new T.Vector3();
  const down=(e:PointerEvent)=>{hover.hidden=true;tap.down(e.pointerId,e.clientX,e.clientY,e.pointerType==='touch'?12:5);};
  const move=(e:PointerEvent)=>{tap.move(e.pointerId,e.clientX,e.clientY);if(e.buttons||amount<.5||e.pointerType==='touch'){hover.hidden=true;return;}const rect=el.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top,index=findTarget(x,y,12);hover.hidden=index<0;renderer.domElement.style.cursor=index<0?'grab':'pointer';if(index>=0){hover.textContent=atlas.parts[index].name;hover.style.left=`${Math.max(8,Math.min(x+14,el.clientWidth-260))}px`;hover.style.top=`${Math.max(8,Math.min(y+18,el.clientHeight-55))}px`;}};
  const cancel=(e:PointerEvent)=>tap.cancel(e.pointerId);
  const up=(e:PointerEvent)=>{
   const validTap=tap.up(e.pointerId,e.clientX,e.clientY);if(!validTap||!ready)return;const rect=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);raycaster.setFromCamera(pointer,camera);
   let nearest=Infinity,found=-1;const hasSolid=atlas.parts.some((p,i)=>p.system!=='skin'&&data[i*4+3]>.5);
   pickers.forEach((mesh,i)=>{if(!mesh||data[i*4+3]<.5||(hasSolid&&atlas.parts[i].system==='skin'))return;worldBox.copy(bounds[i]).applyMatrix4(mesh.matrix);if(!raycaster.ray.intersectBox(worldBox,hitPoint))return;const hits=raycaster.intersectObject(mesh,false).filter(h=>clipPlane.distanceToPoint(h.point)>=0&&(selectedData[i*4+2]<128||membership(RG,U.regKind.value,U.regSide.value,h.point.x-mesh.position.x,h.point.y-mesh.position.y)>=.5));if(hits[0]&&hits[0].distance<nearest){nearest=hits[0].distance;found=i;}});
   if(found<0&&amount>.45)found=findTarget(e.clientX-rect.left,e.clientY-rect.top,e.pointerType==='touch'?24:16);if(found>=0){hover.hidden=true;select.current(atlas.parts[found].id);}
  };
  renderer.domElement.addEventListener('pointerdown',down);renderer.domElement.addEventListener('pointermove',move);renderer.domElement.addEventListener('pointerup',up);renderer.domElement.addEventListener('pointercancel',cancel);
  // ——— Изоляция области: состав, локальная разборка ———
  type RegionInfo={id:string;kind:number;side:number;inSet:Uint8Array;dirs:Float32Array};
  let regionInfo:RegionInfo|null=null,spread=0,savedCam:{p:T.Vector3;t:T.Vector3}|null=null,lastRegionFrame='',prevRegion=false;
  const LAYER:Record<string,number>={skeletal:0,connective:.3,arterial:.6,venous:.6,nervous:.6,cardiac:.6,lymphatic:.6,muscular:1,skin:1.6,hair:1.6};
  const partIndex=new Map(atlas.parts.map((p,i)=>[p.id,i]));
  const buildRegion=(r:NonNullable<SceneState['region']>):RegionInfo=>{
   const [kind,side]=REGION_KIND[r.id as RegionId],n=atlas.parts.length,inSet=new Uint8Array(n);
   r.members.forEach(id=>{const i=partIndex.get(id);if(i!==undefined)inSet[i]=1;});r.clipped.forEach(id=>{const i=partIndex.get(id);if(i!==undefined)inSet[i]=2;});
   const mem:number[]=[];inSet.forEach((v,i)=>{if(v===1)mem.push(i);});
   const center=new T.Vector3();mem.forEach(i=>center.add(centers[i]));center.multiplyScalar(1/Math.max(1,mem.length));
   // ось области — главное направление разброса деталей (рука, нога — вдоль конечности)
   const cov=new Array(9).fill(0);mem.forEach(i=>{const d=centers[i].clone().sub(center),a=[d.x,d.y,d.z];for(let r1=0;r1<3;r1++)for(let c=0;c<3;c++)cov[r1*3+c]+=a[r1]*a[c];});
   let ax=new T.Vector3(0,1,0);for(let it=0;it<40;it++){const v=new T.Vector3(cov[0]*ax.x+cov[1]*ax.y+cov[2]*ax.z,cov[3]*ax.x+cov[4]*ax.y+cov[5]*ax.z,cov[6]*ax.x+cov[7]*ax.y+cov[8]*ax.z);if(v.lengthSq()<1e-14)break;ax=v.normalize();}
   const box=new T.Box3();mem.forEach(i=>box.union(bounds[i]));const size=box.getSize(new T.Vector3()),scale=Math.max(size.x,size.y,size.z,.1);
   const dirs=new Float32Array(n*3);
   mem.forEach(i=>{const d=centers[i].clone().sub(center),along=d.dot(ax),perp=d.clone().addScaledVector(ax,-along);let pl=perp.length();
    if(pl<1e-4){const ref=Math.abs(ax.y)<.9?new T.Vector3(0,1,0):new T.Vector3(1,0,0),u=new T.Vector3().crossVectors(ax,ref).normalize(),w=new T.Vector3().crossVectors(ax,u),a=i*2.399;perp.copy(u).multiplyScalar(Math.cos(a)).addScaledVector(w,Math.sin(a));pl=0;}else perp.multiplyScalar(1/pl);
    // слои расходятся от оси: кости остаются, связки, сосуды и нервы — дальше, мышцы — ещё дальше
    const k=(LAYER[atlas.parts[i].system]??.8)*.12*scale+pl*1.2;dirs.set([perp.x*k+ax.x*along*.35,perp.y*k+ax.y*along*.35,perp.z*k+ax.z*along*.35],i*3);});
   return {id:r.id,kind,side,inSet,dirs};
  };
  // ——— Демонстрация движения мышцы ———
  type MotionInfo={key:string;mode:Uint8Array;force:Uint8Array;pivot:T.Vector3;axis:T.Vector3;muscle:number[];rigid:number[];O:T.Vector3;I:T.Vector3;from:number;to:number;limbBox:T.Box3;frame:T.Box3};
  let motionInfo:MotionInfo|null=null,motionKey='',mAmt=0,mIntro=0,motionCam:{p:T.Vector3;t:T.Vector3}|null=null,prevMotion=false;
  const posOf=(i:number)=>pickers[i]?.geometry.attributes.position.array as ArrayLike<number>|undefined;
  const pts=(i:number,f?:(x:number,y:number,z:number)=>boolean)=>{const a=posOf(i),out:T.Vector3[]=[];if(!a)return out;for(let k=0;k<a.length;k+=3)if(!f||f(a[k],a[k+1],a[k+2]))out.push(new T.Vector3(a[k],a[k+1],a[k+2]));return out;};
  const mean=(v:T.Vector3[])=>{const c=new T.Vector3();v.forEach(p=>c.add(p));return c.multiplyScalar(1/Math.max(1,v.length));};
  const lowest=(v:T.Vector3[])=>v.reduce((a,p)=>p.y<a.y?p:a,v[0]);
  const buildMotion=(m:NonNullable<SceneState['motion']>):MotionInfo|null=>{
   const J=JOINTS[m.joint],sideSign=m.side==='left'?1:-1,Side=m.side==='left'?'Left':'Right',n=atlas.parts.length;
   const find=(name:string)=>atlas.parts.findIndex(p=>p.system==='skeletal'&&p.en===`${Side} ${name}`);
   const ref=find(J.ref);if(ref<0||!posOf(ref))return null;
   const top=bounds[ref].max.y,bot=bounds[ref].min.y,refTop=mean(pts(ref,(x,y)=>y>top-.03)),refBot=mean(pts(ref,(x,y)=>y<bot+.03));
   const across=(v:T.Vector3[])=>{let a=v[0],b=v[0];v.forEach(p=>{if(p.x<a.x)a=p;if(p.x>b.x)b=p;});return b.clone().sub(a).normalize();};
   let pivot:T.Vector3,axis:T.Vector3,D:T.Vector3,B=J.blend;
   // центр и ось сустава берутся из формы костей модели
   if(m.joint==='shoulder-abd'||m.joint==='shoulder-flex'){const t=pts(ref,(x,y)=>y>top-.035),med=t.map(p=>p.x*sideSign).sort((a,b)=>a-b)[t.length>>1];pivot=mean(t.filter(p=>p.x*sideSign<=med));D=refBot.clone().sub(pivot).normalize();axis=m.joint==='shoulder-abd'?new T.Vector3(0,0,1):new T.Vector3(1,0,0);} // головка плечевой кости
   else if(m.joint==='elbow'){pivot=mean(pts(ref,(x,y)=>y<bot+.025));axis=across(pts(ref,(x,y)=>y<bot+.06));D=pivot.clone().sub(refTop).normalize();} // блок и головочка плечевой кости, ось через надмыщелки
   else if(m.joint==='wrist'){const ul=find('ulna');if(ul<0)return null;pivot=mean(pts(ref,(x,y)=>y<bot+.015));axis=lowest(pts(ul)).clone().sub(lowest(pts(ref))).normalize();D=pivot.clone().sub(refTop).normalize();} // ось через шиловидные отростки
   else if(m.joint==='radioulnar'){const ul=find('ulna');if(ul<0)return null;const ub=bounds[ul].min.y;pivot=refTop.clone();const head=mean(pts(ul,(x,y)=>y<ub+.015));axis=head.clone().sub(pivot).normalize();D=axis.clone();B=head.distanceTo(pivot);} // ось от головки лучевой к головке локтевой кости
   else if(m.joint==='hip-flex'||m.joint==='hip-abd'){const t=pts(ref,(x,y)=>y>top-.07),mp=t.reduce((a,p)=>p.x*sideSign<a.x*sideSign?p:a,t[0]);pivot=mean(t.filter(p=>p.distanceTo(mp)<.035));D=refBot.clone().sub(pivot).normalize();axis=m.joint==='hip-abd'?new T.Vector3(0,0,1):new T.Vector3(1,0,0);} // головка бедренной кости
   else if(m.joint==='knee'){pivot=mean(pts(ref,(x,y)=>y<bot+.04));axis=across(pts(ref,(x,y)=>y<bot+.07));D=pivot.clone().sub(refTop).normalize();} // мыщелки бедра, ось через надмыщелки
   else {const fi=find('fibula');if(fi<0)return null;const mm=lowest(pts(ref)),lm=lowest(pts(fi));pivot=mm.clone().add(lm).multiplyScalar(.5);axis=lm.clone().sub(mm).normalize();D=pivot.clone().sub(refTop).normalize();} // ось через верхушки лодыжек
   const limb=((J.limb==='arm'?'arm-':'leg-')+(m.side==='left'?'l':'r')) as RegionId,[kind,side]=REGION_KIND[limb];
   const limbBox=new T.Box3(),inLimb=atlas.parts.map(p=>regionOfPart(atlas,p)===limb);inLimb.forEach((v,i)=>{if(v)limbBox.union(bounds[i]);});
   const mode=new Uint8Array(n),force=new Uint8Array(n),rigid:number[]=[],soft=/ligament|membrane|capsule|retinacul|fascia|bursa|aponeuros|tendon/i;
   atlas.parts.forEach((p,i)=>{const en=p.en??'';
    if(p.system==='skeletal'&&!soft.test(en)){
     if(!inLimb[i]){if(bounds[i].distanceToPoint(pivot)<.06)force[i]=1;return;}
     let r=J.refMoves||J.twist?true:centers[i].clone().sub(pivot).dot(D)>0;if(i===ref)r=!!(J.refMoves||J.twist);if(J.staticBones?.test(en))r=false;if(J.extraRigid?.test(en))r=true;
     mode[i]=r?1:0;force[i]=1;if(r)rigid.push(i);return;}
    if(bounds[i].intersectsBox(limbBox))mode[i]=2;});
   const muscle=m.muscle.map(id=>partIndex.get(id)).filter((i):i is number=>i!==undefined);muscle.forEach(i=>{mode[i]=3;force[i]=1;});
   // направление: дистальный сегмент должен смещаться так, как задано анатомией движения
   const ti=J.testBone?atlas.parts.findIndex(p=>p.system==='skeletal'&&(p.en??'').startsWith(Side)&&J.testBone!.test(p.en??'')):-1;
   const T0=ti>=0?centers[ti].clone():mean(rigid.map(i=>centers[i]));
   const want=J.dir==='anterior'?new T.Vector3(0,0,1):J.dir==='posterior'?new T.Vector3(0,0,-1):J.dir==='lateral'?new T.Vector3(sideSign,0,0):J.dir==='medial'?new T.Vector3(-sideSign,0,0):J.dir==='up'?new T.Vector3(0,1,0):new T.Vector3(0,-1,0);
   if(T0.clone().sub(pivot).applyAxisAngle(axis,.05).add(pivot).sub(T0).dot(want)<0)axis.negate();
   // начало и прикрепление мышцы: концы её главной оси; прикрепление — конец, ближайший к подвижным костям
   const mv:T.Vector3[]=[];muscle.forEach(i=>pts(i).forEach(p=>mv.push(p)));const mc=mean(mv);let ma=D.clone();
   if(mv.length>10){const cov=new Array(9).fill(0);mv.forEach(p=>{const d=[p.x-mc.x,p.y-mc.y,p.z-mc.z];for(let r1=0;r1<3;r1++)for(let c=0;c<3;c++)cov[r1*3+c]+=d[r1]*d[c];});for(let it=0;it<40;it++){const v=new T.Vector3(cov[0]*ma.x+cov[1]*ma.y+cov[2]*ma.z,cov[3]*ma.x+cov[4]*ma.y+cov[5]*ma.z,cov[6]*ma.x+cov[7]*ma.y+cov[8]*ma.z);if(v.lengthSq()<1e-14)break;ma=v.normalize();}}
   const proj=mv.map(p=>p.clone().sub(mc).dot(ma)).sort((a,b)=>a-b),q=(f:number)=>proj[Math.min(proj.length-1,Math.floor(proj.length*f))]??0;
   const E1=mc.clone().addScaledVector(ma,q(.02)),E2=mc.clone().addScaledVector(ma,q(.98));
   const sample:T.Vector3[]=[];rigid.forEach(i=>{const a=pts(i);for(let k=0;k<a.length;k+=Math.max(1,Math.floor(a.length/300)))sample.push(a[k]);});
   const near=(p:T.Vector3)=>sample.reduce((d,s)=>Math.min(d,s.distanceToSquared(p)),Infinity);
   const [O,I]=near(E1)<near(E2)?[E2,E1]:[E1,E2];
   U.mPivot.value.copy(pivot);U.mAxis.value.copy(axis);U.mD.value.copy(D);U.mB.value=B;U.mTwist.value=J.twist?1:0;U.mO.value.copy(O);U.mI.value.copy(I);U.motKind.value=kind;U.motSide.value=side;
   const frame=new T.Box3();atlas.parts.forEach((p,i)=>{if(inLimb[i]&&p.system==='skeletal')frame.union(bounds[i]);});muscle.forEach(i=>frame.union(bounds[i]));
   return {key:m.key,mode,force,pivot,axis,muscle,rigid,O,I,from:m.from,to:m.to,limbBox,frame};
  };
  const viewDir=(view:string)=>view==='front'?new T.Vector3(0,.02,1):view==='back'?new T.Vector3(0,.02,-1):view==='side'?new T.Vector3(1,.02,0):new T.Vector3(.35,.06,1).normalize();
  const frameBox=(box:T.Box3,s:SceneState,dir:T.Vector3,side=true)=>{
   const center=box.getCenter(new T.Vector3()),size=box.getSize(new T.Vector3());const w=el.clientWidth,h=el.clientHeight,mobile=w<768,landscape=w>h&&h<=600;let left=20,right=w-20,top=mobile?175:110,bottom=h-170;if(s.inspectorOpen){if(landscape){right=w-335;top=100;bottom=h-125;}else if(mobile){const sheet=document.querySelector('.detail-sheet')?.getBoundingClientRect(),header=document.querySelector('.identity')?.getBoundingClientRect();top=(header?.bottom??94)+16;bottom=(sheet?.top??h*.58-139)-16;}else{right=w-370;left=w>1100?285:25;}}
   const fp=document.querySelector('.focus-panel')?.getBoundingClientRect(),er=el.getBoundingClientRect();
   if(side&&!mobile&&!s.inspectorOpen){const lp=document.querySelector('.layers-panel')?.getBoundingClientRect(),vc=document.querySelector('.view-controls')?.getBoundingClientRect();if(lp&&lp.width)left=Math.max(left,lp.right-er.left+16);if(vc&&vc.width)right=Math.min(right,vc.left-er.left-16);}if(fp&&fp.height){const fl=fp.left-er.left,fr=fp.right-er.left;if(!mobile&&fl>w*.5)right=Math.min(right,fl-12);else if(!mobile&&fr<w*.5)left=Math.max(left,fr+12);else if((fp.top+fp.bottom)/2-er.top<h/2)top=Math.max(top,fp.bottom-er.top+12);else bottom=Math.min(bottom,fp.top-er.top-12);}
   const availableWidth=Math.max(150,right-left),availableHeight=Math.max(40,bottom-top);camera.setViewOffset(w,h,w/2-(left+right)/2,h/2-(top+bottom)/2,w,h);const distance=Math.max(.07,Math.max(size.y*h/availableHeight,size.x*w/availableWidth/camera.aspect,size.z)/(2*Math.tan(T.MathUtils.degToRad(camera.fov/2)))*1.35);controls.maxDistance=Math.max(40,distance*2);controls.target.copy(center);camera.position.copy(center).add(dir.clone().multiplyScalar(distance));controls.update();dirty=true;
  };
  const project=(v:T.Vector3)=>{const p=v.clone().project(camera);return [(p.x+1)/2*el.clientWidth,(1-p.y)/2*el.clientHeight];};
  let drag:{id:number;x:number;y:number;p0:number;ux:number;uy:number;L:number}|null=null;
  // Потянуть мышцу (или движущуюся кость): смещение указателя к началу мышцы сокращает её
  const grab=(e:PointerEvent)=>{
   const s=latest.current;if(drag){drag=null;return;}if(!s.motion||!motionInfo||!ready||e.target!==renderer.domElement||e.button>0)return;
   const rect=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);raycaster.setFromCamera(pointer,camera);
   const hit=[...motionInfo.muscle,...motionInfo.rigid].some(i=>{const mesh=pickers[i];return !!mesh&&data[i*4+3]>.5&&raycaster.intersectObject(mesh,false).length>0;});if(!hit)return;
   e.stopPropagation();e.preventDefault();
   const I=motionInfo.I.clone().sub(motionInfo.pivot).applyAxisAngle(motionInfo.axis,U.mAngle.value).add(motionInfo.pivot);const [ox,oy]=project(motionInfo.O),[ix,iy]=project(I);let ux=ox-ix,uy=oy-iy;const len=Math.hypot(ux,uy);if(len<25){ux=0;uy=-1;}else{ux/=len;uy/=len;}
   drag={id:e.pointerId,x:e.clientX,y:e.clientY,p0:s.motion.progress,ux,uy,L:Math.max(110,len*.9)};renderer.domElement.style.cursor='grabbing';hover.hidden=true;
  };
  const dragMove=(e:PointerEvent)=>{if(!drag||e.pointerId!==drag.id)return;e.preventDefault();const d=((e.clientX-drag.x)*drag.ux+(e.clientY-drag.y)*drag.uy)/drag.L;motionCb.current?.(Math.min(1,Math.max(0,drag.p0+d)));};
  const dragEnd=(e:PointerEvent)=>{if(drag&&e.pointerId===drag.id){drag=null;renderer.domElement.style.cursor='';}};
  el.addEventListener('pointerdown',grab,true);window.addEventListener('pointermove',dragMove);window.addEventListener('pointerup',dragEnd);window.addEventListener('pointercancel',dragEnd);
  const q=new T.Quaternion(),tmp=new T.Vector3();
  const clock=new T.Clock();let lastExtent=-1,labelKey='';
  const animate=()=>{
   if(disposed)return;frame=requestAnimationFrame(animate);const dt=Math.min(clock.getDelta(),.05),s=latest.current;
   if((s.region?.id??'')!==(regionInfo?.id??''))regionInfo=s.region?buildRegion(s.region):null;
   const mk=s.motion&&ready?s.motion.key:'';if(mk&&mk!==motionKey){motionInfo=buildMotion(s.motion!);motionKey=mk;mAmt=s.motion!.progress;mIntro=0;lastState=null;}
   const changed=lastState?.visible!==s.visible||lastState?.selected!==s.selected||lastState?.isolate!==s.isolate||lastState?.region!==s.region||lastState?.motion!==s.motion;
   const moving=Math.abs(amount-s.explode)>.0001,spreadTarget=s.region?.spread??0,spreadMoving=Math.abs(spread-spreadTarget)>.0001;
   if(moving){amount=T.MathUtils.damp(amount,s.explode,8,dt);dirty=true;}
   if(spreadMoving){spread=T.MathUtils.damp(spread,spreadTarget,8,dt);if(Math.abs(spread-spreadTarget)<.0005)spread=spreadTarget;dirty=true;}
   let motionMoving=false;
   if(motionInfo){const tp=s.motion&&s.motion.key===motionInfo.key?s.motion.progress:mAmt,ti=s.motion&&s.motion.key===motionInfo.key?1:0;const pa=mAmt,pi=mIntro;mAmt=T.MathUtils.damp(mAmt,tp,14,dt);mIntro=T.MathUtils.damp(mIntro,ti,6,dt);if(Math.abs(mAmt-tp)<.0005)mAmt=tp;if(Math.abs(mIntro-ti)<.001)mIntro=ti;
    const fade=(1-T.MathUtils.smoothstep(amount,0,.05))*(1-spread);const deg=(motionInfo.from+(motionInfo.to-motionInfo.from)*mAmt)*mIntro*fade;
    U.mOn.value=1;U.mAngle.value=T.MathUtils.degToRad(deg);U.mBulge.value=.2*mAmt*mIntro*fade;motionMoving=pa!==mAmt||pi!==mIntro||moving||spreadMoving;if(motionMoving)dirty=true;
    if(!s.motion&&mIntro===0){motionInfo=null;motionKey='';U.mOn.value=0;U.mAngle.value=0;lastState=null;}}
   const regionOn=!!(s.region&&regionInfo)&&!s.isolate,inSet=regionInfo?.inSet;
   U.regKind.value=regionOn?regionInfo!.kind:0;U.regSide.value=regionOn?regionInfo!.side:0;
   if(changed||moving||spreadMoving||motionMoving||lastExtent<0){
    const visible=new Set(s.visible),selection=new Set(s.selected);
    const preg=visible.has('pregnancy' as never);
    const shown=(p:Atlas['parts'][number],i:number)=>variantShown(p,preg)&&(s.isolate?selection.has(p.id):regionOn?(inSet![i]>0&&visible.has(p.system as never)&&!(inSet![i]===2&&spread>.15))||selection.has(p.id):visible.has(p.system as never)||selection.has(p.id));
    const visibleParts=atlas.parts.filter((p,i)=>shown(p,i));
    const nextLayoutKey=visibleParts.map(p=>p.id).join(',')+':'+camera.aspect.toFixed(3);
    if(nextLayoutKey!==layoutKey){const layout=createExplosionLayout(visibleParts,camera.aspect);packingWidth=layout.width;packingHeight=layout.height;atlas.parts.forEach((p,i)=>{const cell=layout.cells.get(p.id);offsets[i]=cell?new T.Vector3(cell.x,cell.y+.85,0):centers[i].clone();});layoutKey=nextLayoutKey;if(amount>.05&&!s.isolate)fit(s.view,Math.max(0,(amount-.3)/.7));}

    atlas.parts.forEach((p,i)=>{
     const c=centers[i],destination=offsets[i];let dx=0,dy=0,dz=0;
     if(amount<=.45){const t=amount/.45;const group=SYSTEMS.findIndex(sys=>sys.id===p.system);const angle=group/SYSTEMS.length*Math.PI*2;dx=Math.sin(angle)*t*.48;dy=(c.y-.85)*t*.28;dz=Math.cos(angle)*t*.48;}
     else {const t=(amount-.45)/.55,group=SYSTEMS.findIndex(sys=>sys.id===p.system),angle=group/SYSTEMS.length*Math.PI*2;dx=T.MathUtils.lerp(Math.sin(angle)*.48,destination.x-c.x,t);dy=T.MathUtils.lerp((c.y-.85)*.28,destination.y-c.y,t);dz=T.MathUtils.lerp(Math.cos(angle)*.48,-c.z,t);}
     if(regionOn&&inSet![i]===1){dx+=regionInfo!.dirs[i*3]*spread;dy+=regionInfo!.dirs[i*3+1]*spread;dz+=regionInfo!.dirs[i*3+2]*spread;}
     const selected=selection.has(p.id),mm=motionInfo?motionInfo.mode[i]:0;data.set([dx,dy,dz,(shown(p,i)||(!!motionInfo&&!s.isolate&&motionInfo.force[i]===1))?1:0],i*4);selectedData[i*4]=selected?255:0;selectedData[i*4+1]=mm*60;selectedData[i*4+2]=regionOn&&inSet![i]===2?255:0;
     markerPositions.set(data[i*4+3]>.5?[c.x+dx,c.y+dy,c.z+dz]:[10000,10000,10000],i*3);const mesh=pickers[i];if(mesh){if(mm===1&&U.mAngle.value!==0){q.setFromAxisAngle(motionInfo!.axis,U.mAngle.value);tmp.copy(motionInfo!.pivot).applyQuaternion(q);mesh.quaternion.copy(q);mesh.position.set(dx,dy,dz).add(motionInfo!.pivot).sub(tmp);}else{mesh.quaternion.identity();mesh.position.set(dx,dy,dz);}mesh.updateMatrix();mesh.updateMatrixWorld(true);}
    });partTexture.needsUpdate=true;selectionTexture.needsUpdate=true;markerGeometry.attributes.position.needsUpdate=true;lastState=s;lastExtent=amount;dirty=true;
   }
   const resetNow=s.reset!==lastReset;
   if(s.view!==lastView||s.reset!==lastReset){fit(s.view,amount);lastView=s.view;lastReset=s.reset;}
   const regionFraming=!!s.region&&!s.isolate&&amount<=.45;
   if(moving&&!s.isolate&&!regionFraming)fit(amount>.5?'front':s.view,Math.max(0,(amount-.3)/.7));
   const isolateKey=s.isolate?s.selected.join(',')+':'+s.reset+':'+s.inspectorOpen+':'+camera.aspect:'';
   if(isolateKey!==lastIsolate||(s.isolate&&moving)){
    if(s.isolate){const box=new T.Box3();atlas.parts.forEach((p,i)=>{if(s.selected.includes(p.id))box.union(bounds[i].clone().translate(new T.Vector3(data[i*4],data[i*4+1],data[i*4+2])));});
     if(!box.isEmpty())frameBox(box,s,new T.Vector3(.2,.1,1).normalize(),false);
    }else if(lastIsolate){camera.clearViewOffset();fit(s.view,amount);}
    lastIsolate=isolateKey;
   }
   // Изоляция области: запомнить камеру при входе, показать область, вернуть камеру при выходе
   if(s.region&&!prevRegion)savedCam={p:camera.position.clone(),t:controls.target.clone()};
   if(!s.region&&prevRegion){camera.clearViewOffset();if(savedCam&&!resetNow&&!s.isolate){camera.position.copy(savedCam.p);controls.target.copy(savedCam.t);controls.update();}else fit(s.view,amount);savedCam=null;dirty=true;}
   prevRegion=!!s.region;
   const rkey=regionFraming?`${s.region!.id}:${s.reset}:${s.view}:${s.inspectorOpen}:${camera.aspect}:${s.region!.members.length}:${s.visible.join()}`:'';
   if(regionFraming&&(rkey!==lastRegionFrame||spreadMoving||moving)){const box=new T.Box3();atlas.parts.forEach((p,i)=>{if(data[i*4+3]>.5&&inSet&&inSet[i]===1)box.union(bounds[i].clone().translate(new T.Vector3(data[i*4],data[i*4+1],data[i*4+2])));});if(box.isEmpty())atlas.parts.forEach((p,i)=>{if(inSet&&inSet[i]===1)box.union(bounds[i]);});if(!box.isEmpty())frameBox(box,s,viewDir(s.view));}
   else if(!regionFraming&&lastRegionFrame&&s.region&&!s.isolate)camera.clearViewOffset();
   lastRegionFrame=rkey;
   // Демонстрация движения вне изоляции: приблизить конечность, по окончании вернуть камеру
   if(s.motion&&!prevMotion&&!s.region&&!s.isolate&&motionInfo){motionCam={p:camera.position.clone(),t:controls.target.clone()};const b=(motionInfo.frame.isEmpty()?motionInfo.limbBox:motionInfo.frame).clone().expandByScalar(.03);frameBox(b,s,viewDir(s.view));}
   if(!s.motion&&prevMotion&&motionCam&&!s.region&&!s.isolate){camera.clearViewOffset();if(!resetNow){camera.position.copy(motionCam.p);controls.target.copy(motionCam.t);controls.update();}motionCam=null;dirty=true;}
   if(s.motion&&motionInfo)prevMotion=true;else if(!s.motion)prevMotion=false;
   controls.enableRotate=amount<.8;controls.mouseButtons.LEFT=amount<.8?T.MOUSE.ROTATE:T.MOUSE.PAN;controls.touches.ONE=amount<.8?T.TOUCH.ROTATE:T.TOUCH.PAN;ground.visible=platform.visible=ring.visible=innerRing.visible=amount<.5&&!s.isolate&&!s.region;markers.visible=amount>.75;controls.autoRotate=s.rotate&&!s.isolate&&amount<.4;controls.autoRotateSpeed=.65;controls.update();if(controls.autoRotate)dirty=true;
   const c=s.clip,ck=c&&c.on?`${c.axis}:${c.pos}`:'off';if(ck!==clipKey){if(c&&c.on){clipPlane.normal.set(c.axis==='x'?-1:0,c.axis==='y'?-1:0,c.axis==='z'?-1:0);clipPlane.constant=c.pos;}else{clipPlane.normal.set(0,-1,0);clipPlane.constant=1000;}clipKey=ck;dirty=true;}
   const lk=(s.labels?1:0)+':'+s.visible.join(',')+':'+s.isolate;if(lk!==labelKey){labelKey=lk;dirty=true;}
   if(dirty){renderer.render(scene,camera);drawLabels(s);targets=[];if(amount>.45){const hasSolid=atlas.parts.some((p,i)=>p.system!=='skin'&&data[i*4+3]>.5);atlas.parts.forEach((p,i)=>{if(data[i*4+3]<.5||(hasSolid&&p.system==='skin'))return;let left=Infinity,right=-Infinity,top=Infinity,bottom=-Infinity;for(let corner=0;corner<8;corner++){projected.set(p.bounds[(corner&1)?1:0][0]+data[i*4],p.bounds[(corner&2)?1:0][1]+data[i*4+1],p.bounds[(corner&4)?1:0][2]+data[i*4+2]).project(camera);const x=(projected.x+1)*el.clientWidth/2,y=(1-projected.y)*el.clientHeight/2;left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);}projected.copy(centers[i]).add(new T.Vector3(data[i*4],data[i*4+1],data[i*4+2])).project(camera);if(projected.z< -1||projected.z>1)return;targets.push({index:i,x:(projected.x+1)*el.clientWidth/2,y:(1-projected.y)*el.clientHeight/2,left,right,top,bottom});});}dirty=false;}

  };animate();
  const contextLost=(e:Event)=>{e.preventDefault();onError('Устройство приостановило 3D. Перезагрузите страницу.');};renderer.domElement.addEventListener('webglcontextlost',contextLost);
  return()=>{disposed=true;abort.abort();cancelAnimationFrame(frame);observer.disconnect();controls.dispose();geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());scene.traverse(o=>{if(o instanceof T.Mesh&&!geometries.includes(o.geometry)){o.geometry.dispose();const ms=Array.isArray(o.material)?o.material:[o.material];ms.forEach(m=>m.dispose());}});env.dispose();partTexture.dispose();selectionTexture.dispose();markerGeometry.dispose();markerMaterial.dispose();hover.remove();labelLayer.remove();el.removeEventListener('pointerdown',grab,true);window.removeEventListener('pointermove',dragMove);window.removeEventListener('pointerup',dragEnd);window.removeEventListener('pointercancel',dragEnd);renderer.dispose();renderer.domElement.remove();};
 },[atlas,quality]);
 return <div className="scene" ref={host}/>;
}
