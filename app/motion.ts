import type {Atlas,Part} from './anatomy';
/**
 * Демонстрация движения мышцы.
 * Сустав задаётся по костям модели: центр вращения и ось вычисляются из геометрии (головка плечевой кости,
 * надмыщелки, лодыжки и т. д.), направление — по анатомическому смыслу движения, амплитуда — по нормам
 * подвижности суставов (нейтральное — нулевое — положение анатомической стойки).
 */
export type JointId='shoulder-abd'|'shoulder-flex'|'elbow'|'radioulnar'|'wrist'|'hip-flex'|'hip-abd'|'knee'|'ankle';
/** Направление, в котором смещается дистальный сегмент при положительном угле. */
export type Dir='anterior'|'posterior'|'lateral'|'medial'|'up'|'down';
export interface JointDef {name:string;limb:'arm'|'leg';/** кость, от которой считается ось/центр */ref:string;dir:Dir;/** кости, которые не двигаются, хотя лежат дистальнее */staticBones?:RegExp;/** кости, которые двигаются всегда */extraRigid?:RegExp;/** точка, по которой проверяется направление */testBone?:RegExp;/** ширина зоны изгиба мягких тканей, м; для скручивания предплечья — вся его длина */blend:number;twist?:boolean;/** опорная кость сама движется (плечо, бедро) */refMoves?:boolean}
export const JOINTS:Record<JointId,JointDef>={
 'shoulder-abd':{name:'Плечевой сустав',limb:'arm',ref:'humerus',dir:'lateral',blend:.03,refMoves:true},
 'shoulder-flex':{name:'Плечевой сустав',limb:'arm',ref:'humerus',dir:'anterior',blend:.03,refMoves:true},
 elbow:{name:'Локтевой сустав',limb:'arm',ref:'humerus',dir:'anterior',blend:.025},
 radioulnar:{name:'Лучелоктевые суставы',limb:'arm',ref:'radius',dir:'anterior',staticBones:/ulna|humerus/i,testBone:/first metacarpal/i,blend:0,twist:true},
 wrist:{name:'Лучезапястный сустав',limb:'arm',ref:'radius',dir:'anterior',blend:.015},
 'hip-flex':{name:'Тазобедренный сустав',limb:'leg',ref:'femur',dir:'anterior',blend:.04,refMoves:true},
 'hip-abd':{name:'Тазобедренный сустав',limb:'leg',ref:'femur',dir:'lateral',blend:.04,refMoves:true},
 knee:{name:'Коленный сустав',limb:'leg',ref:'femur',dir:'posterior',extraRigid:/patella/i,blend:.03},
 ankle:{name:'Голеностопный сустав',limb:'leg',ref:'tibia',dir:'up',blend:.02},
};
export interface MotionSpec {match:RegExp;joint:JointId;/** угол в начале и в конце сокращения, градусы, в направлении JointDef.dir */from:number;to:number;title:string;actions:string}
const S=(match:RegExp,joint:JointId,from:number,to:number,title:string,actions:string):MotionSpec=>({match,joint,from,to,title,actions});
export const MOTIONS:MotionSpec[]=[
 S(/biceps brachii/i,'elbow',0,140,'Сгибание предплечья в локте','Сгибает предплечье в локтевом суставе и поворачивает его ладонью вверх (супинация); слабо сгибает плечо.'),
 S(/^(left|right) brachialis$/i,'elbow',0,140,'Сгибание предплечья в локте','Главный сгибатель локтевого сустава при любом положении предплечья.'),
 S(/brachioradialis/i,'elbow',0,130,'Сгибание предплечья в локте','Сгибает предплечье в локте, сильнее всего — в положении между пронацией и супинацией.'),
 S(/triceps brachii/i,'elbow',130,0,'Разгибание предплечья в локте','Разгибает предплечье в локтевом суставе; длинная головка также разгибает и приводит плечо.'),
 S(/anconeus/i,'elbow',130,0,'Разгибание предплечья в локте','Помогает трёхглавой мышце разгибать локоть и натягивает капсулу сустава.'),
 S(/acromial part of .*deltoid/i,'shoulder-abd',0,90,'Отведение плеча','Акромиальная часть отводит плечо до горизонтали.'),
 S(/clavicular part of .*deltoid/i,'shoulder-flex',0,90,'Сгибание плеча (подъём руки вперёд)','Ключичная часть сгибает плечо и поворачивает его внутрь.'),
 S(/spinal part of .*deltoid/i,'shoulder-flex',0,-40,'Разгибание плеча (отведение руки назад)','Остистая часть разгибает плечо и поворачивает его наружу.'),
 S(/supraspinatus/i,'shoulder-abd',0,90,'Отведение плеча','Начинает отведение плеча и удерживает головку плечевой кости в суставной впадине.'),
 S(/clavicular part of .*pectoralis major/i,'shoulder-flex',0,90,'Сгибание плеча','Ключичная часть сгибает плечо; вся мышца приводит плечо и поворачивает его внутрь.'),
 S(/(sternocostal|abdominal) part of .*pectoralis major/i,'shoulder-abd',70,0,'Приведение плеча','Приводит плечо к туловищу и поворачивает его внутрь.'),
 S(/teres major/i,'shoulder-abd',60,0,'Приведение плеча','Приводит, разгибает и поворачивает плечо внутрь.'),
 S(/coracobrachialis/i,'shoulder-flex',0,60,'Сгибание плеча','Сгибает и приводит плечо.'),
 S(/flexor carpi (radialis|ulnaris)|palmaris longus/i,'wrist',0,75,'Сгибание кисти','Сгибает кисть в лучезапястном суставе.'),
 S(/extensor carpi (radialis|ulnaris)/i,'wrist',0,-65,'Разгибание кисти','Разгибает кисть в лучезапястном суставе.'),
 S(/pronator (teres|quadratus)/i,'radioulnar',0,150,'Пронация предплечья','Поворачивает предплечье ладонью назад (вниз): лучевая кость вращается вокруг локтевой.'),
 S(/supinator/i,'radioulnar',150,0,'Супинация предплечья','Поворачивает предплечье ладонью вперёд (вверх).'),
 S(/psoas major|^(left|right) iliacus$/i,'hip-flex',0,80,'Сгибание бедра','Сгибает бедро в тазобедренном суставе (подъём ноги вперёд).'),
 S(/rectus femoris/i,'knee',90,0,'Разгибание голени в колене','Разгибает голень в коленном суставе и сгибает бедро.'),
 S(/vastus/i,'knee',90,0,'Разгибание голени в колене','Разгибает голень в коленном суставе.'),
 S(/gluteus maximus/i,'hip-flex',80,-10,'Разгибание бедра','Разгибает бедро (подъём из приседа, по лестнице) и поворачивает его наружу.'),
 S(/gluteus (medius|minimus)|tensor fasciae latae/i,'hip-abd',0,40,'Отведение бедра','Отводит бедро и удерживает таз при ходьбе.'),
 S(/adductor (longus|brevis|magnus|minimus)|pectineus|gracilis/i,'hip-abd',35,0,'Приведение бедра','Приводит бедро к средней линии.'),
 S(/biceps femoris|semitendinosus|semimembranosus/i,'knee',0,120,'Сгибание голени в колене','Сгибает голень в колене и разгибает бедро.'),
 S(/gastrocnemius|soleus/i,'ankle',0,-40,'Подошвенное сгибание стопы','Опускает носок — подъём на носки, толчок при ходьбе.'),
 S(/tibialis anterior/i,'ankle',0,20,'Тыльное сгибание стопы','Поднимает носок стопы и поворачивает стопу внутрь.'),
];
export const sideOf=(p:Part):'left'|'right'|null=>/\bleft\b/i.test(p.en??'')?'left':/\bright\b/i.test(p.en??'')?'right':null;
export type MotionInfo={ok:true;spec:MotionSpec;joint:JointDef;side:'left'|'right';muscle:string[];proximal:string;distalTest?:string}|{ok:false;reason:string};
/** Есть ли для этой мышцы проверенное движение и все нужные кости в текущей модели. */
export function motionFor(atlas:Atlas,p:Part):MotionInfo{
 if(p.system!=='muscular')return {ok:false,reason:'Демонстрация движения доступна только для мышц.'};
 const spec=MOTIONS.find(m=>m.match.test(p.en??''));
 if(!spec)return {ok:false,reason:'Для этой мышцы нет проверенной модели движения: она действует на несколько суставов сразу, на мелкие суставы кисти, стопы, позвоночника или лица, либо её действие зависит от положения тела. Чтобы не показывать выдуманное движение, демонстрация для неё отключена.'};
 const side=sideOf(p);if(!side)return {ok:false,reason:'Не удалось определить сторону тела для этой мышцы.'};
 const joint=JOINTS[spec.joint],Side=side[0].toUpperCase()+side.slice(1);
 const need=joint.limb==='arm'?['humerus','radius','ulna']:['femur','tibia'];
 if(joint.limb==='leg'&&spec.joint==='ankle')need.push('fibula','talus');
 const has=(b:string)=>atlas.parts.some(q=>q.system==='skeletal'&&(q.en??'')===`${Side} ${b}`);
 const lack=need.filter(b=>!has(b));
 if(lack.length)return {ok:false,reason:'В этой модели нет костей, к которым крепится мышца, поэтому показать движение сустава нельзя.'};
 const muscle=atlas.parts.filter(q=>q.system==='muscular'&&sideOf(q)===side&&spec.match.test(q.en??'')&&MOTIONS.find(m=>m.match.test(q.en??''))===spec&&(q.en??'').replace(/\b(left|right)\b/i,'').replace(/^(long|short|lateral|medial|humeral|ulnar|oblique|transverse) head of /i,'')===(p.en??'').replace(/\b(left|right)\b/i,'').replace(/^(long|short|lateral|medial|humeral|ulnar|oblique|transverse) head of /i,'')).map(q=>q.id);
 return {ok:true,spec,joint,side,muscle:muscle.length?muscle:[p.id],proximal:`${Side} ${joint.ref}`};
}
