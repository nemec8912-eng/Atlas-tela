import {createRoot} from 'react-dom/client';
import Home from '../app/page';
import '../app/globals.css';
createRoot(document.getElementById('root')!).render(<Home/>);
// Офлайн-режим: работает там, где разрешены service worker'ы (например, GitHub Pages).
try{if('serviceWorker' in navigator&&location.protocol==='https:'&&!/claude\.ai|claudeusercontent|claude\.site/.test(location.hostname))addEventListener('load',()=>{navigator.serviceWorker.register('sw.js').catch(()=>{});});}catch{}
