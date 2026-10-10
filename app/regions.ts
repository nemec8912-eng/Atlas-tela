import type {Atlas,Part} from './anatomy';
/** Области тела для изоляции. Координаты модели: метры, Y — вверх, +X — левая сторона тела, +Z — вперёд. */
export type RegionId='head'|'torso'|'arm-l'|'arm-r'|'leg-l'|'leg-r';
export const REGION_NAMES:Record<RegionId,string>={head:'Голова и шея',torso:'Туловище','arm-l':'Левая рука','arm-r':'Правая рука','leg-l':'Левая нога','leg-r':'Правая нога'};
/** Границы областей сняты с поверхности кожи каждой модели (промежутки между рукой и туловищем, промежность, шея). */
export interface RegionGeometry {armY:number[];armX:number[];armMinY:number;armMaxY:number;legC0:number;legC1:number;headY:number;headX:number}
const MALE:RegionGeometry={armY:[.6,.98,1.0,1.1,1.2,1.3,1.46,1.6],armX:[.19,.19,.168,.158,.165,.16,.15,.15],armMinY:.6,armMaxY:1.46,legC0:.8,legC1:.6,headY:1.44,headX:.11};
// Женская модель стоит с отведёнными руками
const FEMALE:RegionGeometry={armY:[.7,.8,.9,1.0,1.1,1.2,1.42,1.6],armX:[.29,.28,.25,.2,.168,.155,.15,.15],armMinY:.7,armMaxY:1.42,legC0:.72,legC1:.6,headY:1.43,headX:.11};
export const regionGeometry=(atlas:Atlas):RegionGeometry=>(atlas as {sex?:string}).sex==='female'?FEMALE:MALE;
export const REGION_KIND:Record<RegionId,[number,number]>={'arm-l':[1,1],'arm-r':[1,-1],'leg-l':[2,1],'leg-r':[2,-1],head:[3,0],torso:[4,0]};
const lerpTable=(ys:number[],xs:number[],y:number)=>{if(y<=ys[0])return xs[0];for(let k=1;k<ys.length;k++)if(y<=ys[k]){const t=(y-ys[k-1])/(ys[k]-ys[k-1]);return xs[k-1]+(xs[k]-xs[k-1])*t;}return xs[xs.length-1];};
const ss=(a:number,b:number,x:number)=>{const t=Math.min(1,Math.max(0,(x-a)/(b-a)));return t*t*(3-2*t);};
/** Плавная принадлежность точки области (0…1); та же формула работает в шейдере. */
export function membership(g:RegionGeometry,kind:number,side:number,x:number,y:number,m=.012){
 const arm=(s:number)=>ss(-m,m,s*x-lerpTable(g.armY,g.armX,y))*ss(g.armMinY-m,g.armMinY+m,y)*(1-ss(g.armMaxY-m,g.armMaxY+m,y));
 const leg=(s:number)=>ss(-m,m,g.legC0+g.legC1*Math.abs(x)-y)*ss(-m,m,s*x)*(1-arm(s));
 const head=ss(-m,m,y-g.headY)*ss(-m,m,g.headX-Math.abs(x));
 if(kind===1)return arm(side);if(kind===2)return leg(side);if(kind===3)return head;
 return Math.max(0,1-arm(1)-arm(-1)-leg(1)-leg(-1)-head);
}
const ORGANS=new Set(['respiratory','digestive','cardiac','urinary','reproductive','endocrine','lymphatic','mammary','pregnancy']);
// Мышцы ягодичной области анатомически относятся к нижней конечности
const HIP=/gluteus|piriformis|obturator|gemellus|quadratus femoris|tensor fasciae latae/i;
const center=(p:Part)=>[0,1,2].map(k=>(p.bounds[0][k]+p.bounds[1][k])/2);
/** Область, к которой относится деталь (по центру её габарита). Внутренние органы — только туловище или голова. */
export function regionOfPart(atlas:Atlas,p:Part):RegionId{
 const g=regionGeometry(atlas),[x,y]=center(p);
 if(p.system==='muscular'&&HIP.test(p.en??''))return x>=0?'leg-l':'leg-r';
 const order:RegionId[]=ORGANS.has(p.system)?['head','torso']:['arm-l','arm-r','leg-l','leg-r','head','torso'];
 for(const r of order){const [k,s]=REGION_KIND[r];if(membership(g,k,s,x,y,0)>=.5)return r;}
 return 'torso';
}
const vol=(b:number[][])=>Math.max(1e-9,(b[1][0]-b[0][0])*(b[1][1]-b[0][1])*(b[1][2]-b[0][2]));
/** Состав области: детали внутри неё целиком и «сквозные» детали (кожа, длинные сосуды), которые показываются обрезанными по границе области. */
export function regionParts(atlas:Atlas,region:RegionId){
 const members:string[]=[],lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
 for(const p of atlas.parts)if(regionOfPart(atlas,p)===region){members.push(p.id);for(let k=0;k<3;k++){lo[k]=Math.min(lo[k],p.bounds[0][k]);hi[k]=Math.max(hi[k],p.bounds[1][k]);}}
 const set=new Set(members),clipped:string[]=[];
 if(members.length)for(const p of atlas.parts){if(set.has(p.id))continue;const b=p.bounds;let ov=1;for(let k=0;k<3;k++)ov*=Math.max(0,Math.min(b[1][k],hi[k])-Math.max(b[0][k],lo[k]));const diag=Math.hypot(b[1][0]-b[0][0],b[1][1]-b[0][1],b[1][2]-b[0][2]);if(ov/vol(b)>=.3&&diag>.2)clipped.push(p.id);}
 return {members,clipped};
}
