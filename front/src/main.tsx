import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { store } from './app/store'
import { AppRouter } from './router/AppRouter'
import { applyTheme, getInitialTheme } from './shared/theme/theme'
import './styles/theme.css'
import './styles/forms.css'
import './index.css'

const queryClient = new QueryClient()
applyTheme(getInitialTheme())

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <AppRouter />
      </QueryClientProvider>
    </Provider>
  </StrictMode>,
)
