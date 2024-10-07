import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {
    createBrowserRouter,
    RouterProvider
} from "react-router-dom"
import './index.css'
import Root from './routes/root.tsx'
import AnnotationPage from './routes/AnnotationPage.tsx'

const router = createBrowserRouter([
    {path: "/", element: <Root />},
    {path: "annotate", element:<AnnotationPage />}
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
      <RouterProvider router={router} />
  </StrictMode>,
)
