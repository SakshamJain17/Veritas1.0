"use client";
import {createContext,useCallback,useContext,useEffect,useState} from "react";
type Preference="light"|"dark"|"system";
type Theme="light"|"dark";
type Appearance={preference:Preference;resolved:Theme;setPreference:(value:Preference)=>void};
const ThemeContext=createContext<Appearance|null>(null);
const valid=(value:string|null|undefined):value is Preference=>value==="light"||value==="dark"||value==="system";
function readPreference():Preference{try{const cookie=document.cookie.match(/(?:^|;\s*)veritas-theme=(light|dark|system)(?:;|$)/)?.[1];if(valid(cookie))return cookie;const stored=localStorage.getItem("veritas-theme");if(valid(stored))return stored}catch{}return "system"}
function apply(preference:Preference):Theme{const theme=preference==="system"?(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"):preference;document.documentElement.dataset.theme=theme;document.documentElement.dataset.themePreference=preference;document.documentElement.style.colorScheme=theme;document.documentElement.classList.toggle("dark",theme==="dark");document.querySelectorAll<HTMLLinkElement>('link[rel="icon"]').forEach(icon=>{icon.href=`/brand/veritas-mark-${theme}.svg`;icon.removeAttribute("media")});return theme}
export function ThemeProvider({children}:{children:React.ReactNode}){
 const[preference,setState]=useState<Preference>("system"),[resolved,setResolved]=useState<Theme>("light");
 const setPreference=useCallback((value:Preference)=>{setState(value);setResolved(apply(value));try{localStorage.setItem("veritas-theme",value)}catch{}document.cookie=`veritas-theme=${value};path=/;max-age=31536000;samesite=lax${location.protocol==="https:"?";secure":""}`},[]);
 useEffect(()=>{const sync=()=>{const value=readPreference();setState(value);setResolved(apply(value))};sync();const media=matchMedia("(prefers-color-scheme: dark)");const systemChanged=()=>{if(readPreference()==="system")setResolved(apply("system"))};media.addEventListener("change",systemChanged);window.addEventListener("storage",sync);window.addEventListener("focus",sync);return()=>{media.removeEventListener("change",systemChanged);window.removeEventListener("storage",sync);window.removeEventListener("focus",sync)}},[]);
 return <ThemeContext.Provider value={{preference,resolved,setPreference}}>{children}</ThemeContext.Provider>;
}
function ThemeIcon({mode}:{mode:Preference}){return <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{mode==="light"?<><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></>:mode==="dark"?<path d="M20.9 13.1A8.8 8.8 0 0 1 10.9 3.1a9 9 0 1 0 10 10Z"/>:<><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8m-4-4v4"/></>}</svg>}
export function ThemeSwitch({compact=false}:{compact?:boolean}){
 const theme=useContext(ThemeContext);
 if(!theme)return null;
 const next=theme.resolved==="dark"?"light":"dark";
 const label=`Switch to ${next} mode`;
 return <div className={`theme-switch theme-switch--icon ${compact?"theme-switch--compact":""}`}><button type="button" className="theme-trigger" onClick={()=>theme.setPreference(next)} aria-label={label} title={label}><span className="theme-toggle-sun"><ThemeIcon mode="light"/></span><span className="theme-toggle-moon"><ThemeIcon mode="dark"/></span></button></div>;
}
