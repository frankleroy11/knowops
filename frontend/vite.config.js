import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({base:'/ui/',plugins:[vue()],server:{port:5173,strictPort:true,host:'127.0.0.1',proxy:{'/api':'http://127.0.0.1:8010'}}})
