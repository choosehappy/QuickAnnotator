import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {
    createBrowserRouter,
    RouterProvider
} from "react-router-dom"
import './index.css'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css';
import Root from './routes/root.tsx'
import AnnotationPage from './routes/annotationPage.tsx'
import ProjectPage from './routes/projectPage.tsx'
import LandingPage from './routes/landingPage.tsx'

const router = createBrowserRouter([
    {path: "/", element: <Root />, children: [
        {path: "/home", element:<LandingPage />},
        {path: "project", element:<ProjectPage />},
        {path: "annotate", element:<AnnotationPage />}
    ]
    }
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
      <RouterProvider router={router} />
  </StrictMode>,
)
