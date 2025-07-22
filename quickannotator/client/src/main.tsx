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
import { CookiesProvider } from 'react-cookie'

const router = createBrowserRouter([
    {path: "/", element: <Root />, children: [
        {path: "/", element:<LandingPage />},
        {path: "/project/:projectid", element:<ProjectPage />},
        {path: "/project/:projectid/annotate/:imageid", element:<AnnotationPage />}

    ]}
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CookiesProvider>
        <RouterProvider router={router} />
    </CookiesProvider>
  </StrictMode>,
)
