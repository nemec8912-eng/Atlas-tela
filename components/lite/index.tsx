import {createContext,forwardRef,useContext,useEffect,useRef,type ReactNode,type HTMLAttributes,type ButtonHTMLAttributes} from 'react';
const cx=(...c:(string|false|undefined|null)[])=>c.filter(Boolean).join(' ');

export function Button({variant,className,...p}:ButtonHTMLAttributes<HTMLButtonElement>&{variant?:string}){
 return <button type="button" className={cx('lite-btn',variant!=='ghost'&&'lite-btn-solid',className)} {...p}/>;
}
export function Badge({variant,className,...p}:HTMLAttributes<HTMLSpanElement>&{variant?:string}){
 return <span className={cx('lite-badge',variant&&`lite-badge-${variant}`,className)} {...p}/>;
}
export function Switch({checked,onCheckedChange,...p}:{checked:boolean;onCheckedChange:(v:boolean)=>void}&Omit<ButtonHTMLAttributes<HTMLButtonElement>,'onChange'>){
 return <button type="button" role="switch" aria-checked={checked} data-slot="switch" data-checked={checked?'':undefined} className="lite-switch" onClick={()=>onCheckedChange(!checked)} {...p}><span data-slot="switch-thumb" className="lite-switch-thumb"/></button>;
}
export function Slider({value,onValueChange,min=0,max=100,step=1,...p}:{value:number[];onValueChange:(v:number[])=>void;min?:number;max?:number;step?:number}&Omit<HTMLAttributes<HTMLDivElement>,'onChange'>){
 const pct=((value[0]-min)/(max-min))*100;
 return <div data-slot="slider" className="lite-slider"><input type="range" min={min} max={max} step={step} value={value[0]} onChange={e=>onValueChange([Number(e.target.value)])} style={{['--pct' as string]:`${pct}%`}} {...(p as object)}/></div>;
}

/* Sheet */
const SheetCtx=createContext<{open:boolean;setOpen:(v:boolean)=>void;modal:boolean;dismiss:boolean}>({open:false,setOpen:()=>{},modal:true,dismiss:true});
export function Sheet({open,onOpenChange,modal=true,disablePointerDismissal,children}:{open:boolean;onOpenChange:(v:boolean)=>void;modal?:boolean;disablePointerDismissal?:boolean;children:ReactNode}){
 useEffect(()=>{if(!open)return;const k=(e:KeyboardEvent)=>{if(e.key==='Escape')onOpenChange(false);};window.addEventListener('keydown',k);return()=>window.removeEventListener('keydown',k);},[open,onOpenChange]);
 return <SheetCtx.Provider value={{open,setOpen:onOpenChange,modal,dismiss:!disablePointerDismissal}}>{open?children:null}</SheetCtx.Provider>;
}
export function SheetContent({className,children,initialFocus,showCloseButton=true}:{className?:string;children:ReactNode;initialFocus?:{current:HTMLElement|null};showCloseButton?:boolean}){
 const {setOpen,modal,dismiss}=useContext(SheetCtx);
 useEffect(()=>{initialFocus?.current?.focus({preventScroll:true});},[]);
 return <>{modal&&<div data-slot="sheet-overlay" className="lite-overlay" onClick={()=>dismiss&&setOpen(false)}/>}<div role="dialog" data-slot="sheet-content" className={cx('lite-sheet',className)}>{showCloseButton&&<button type="button" data-slot="sheet-close" className="lite-close" aria-label="Закрыть" onClick={()=>setOpen(false)}>✕</button>}{children}</div></>;
}
export const SheetTitle=forwardRef<HTMLHeadingElement,HTMLAttributes<HTMLHeadingElement>>(function SheetTitle(p,ref){return <h2 ref={ref} data-slot="sheet-title" {...p}/>;});
export function SheetDescription({className,...p}:HTMLAttributes<HTMLDivElement>){return <div data-slot="sheet-description" className={className} {...p}/>;}

/* Combobox (минимальная версия под поиск) */
type CB={items:unknown[];choose:(v:unknown)=>void;input:string;setInput:(s:string)=>void;close:()=>void;label:(v:unknown)=>string};
const CbCtx=createContext<CB|null>(null);
export function Combobox<T>({items,onValueChange,inputValue,onInputValueChange,onOpenChange,itemToStringLabel,children}:{items:T[];value:T|null;onValueChange:(v:T|null)=>void;inputValue:string;onInputValueChange:(s:string)=>void;itemToStringLabel:(v:T)=>string;filter:null;open:boolean;onOpenChange:(o:boolean)=>void;children:ReactNode}){
 return <CbCtx.Provider value={{items,choose:v=>onValueChange(v as T),input:inputValue,setInput:onInputValueChange,close:()=>onOpenChange(false),label:v=>itemToStringLabel(v as T)}}><div className="lite-combobox">{children}</div></CbCtx.Provider>;
}
export function ComboboxInput({autoFocus,placeholder,...p}:{autoFocus?:boolean;placeholder?:string;showTrigger?:boolean;'aria-label'?:string}){
 const c=useContext(CbCtx)!,ref=useRef<HTMLInputElement>(null);
 useEffect(()=>{if(autoFocus)ref.current?.focus();},[]);
 return <div data-slot="input-group" className="lite-input-group"><input ref={ref} type="search" enterKeyHint="search" autoComplete="off" placeholder={placeholder} aria-label={p['aria-label']} value={c.input} onChange={e=>c.setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Escape')c.close();if(e.key==='Enter'&&c.items[0])c.choose(c.items[0]);}}/></div>;
}
export function ComboboxContent({className,children}:{className?:string;children:ReactNode}){return <div className={cx('lite-cb-content',className)} role="listbox">{children}</div>;}
export function ComboboxEmpty({children}:{children:ReactNode}){const c=useContext(CbCtx)!;return c.items.length?null:<div className="lite-cb-empty">{children}</div>;}
export function ComboboxList({children}:{children:(item:any)=>ReactNode}){const c=useContext(CbCtx)!;return <>{c.items.map(i=>children(i))}</>;}
export function ComboboxItem({value,children}:{value:unknown;children:ReactNode}){const c=useContext(CbCtx)!;return <button type="button" role="option" data-slot="combobox-item" className="lite-cb-item" onClick={()=>c.choose(value)}>{children}</button>;}
