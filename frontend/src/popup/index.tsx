import React from 'react';
import Popup from "./Popup"
import { createRoot } from "react-dom/client"
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import '../index.css'

const queryClient = new QueryClient();

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <Popup />
      </QueryClientProvider>
    </React.StrictMode>
  );
}