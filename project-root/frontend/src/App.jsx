import React from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import { AppBar, Toolbar, Typography, Container, Box, Button, IconButton, Tooltip } from '@mui/material'
import HomeIcon from '@mui/icons-material/Home'
import FolderIcon from '@mui/icons-material/Folder'
import DescriptionIcon from '@mui/icons-material/Description'
import Home from './pages/Home'
import Parser from './pages/Parser'

function App() {
  return (
    <React.Fragment>
      <AppBar position="static">
        <Toolbar>
          <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
            <DescriptionIcon sx={{ mr: 1 }} />
            <Typography variant="h6" component="div">
              Обработчик файлов
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Главная - Поиск поврежденных файлов">
              <Button 
                color="inherit" 
                component={Link} 
                to="/"
                startIcon={<HomeIcon />}
                sx={{ 
                  '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' },
                  borderRadius: 2
                }}
              >
                Главная
              </Button>
            </Tooltip>
            <Tooltip title="Парсер - Обработка и анализ файлов">
              <Button 
                color="inherit" 
                component={Link} 
                to="/parser"
                startIcon={<FolderIcon />}
                sx={{ 
                  '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' },
                  borderRadius: 2
                }}
              >
                Парсер
              </Button>
            </Tooltip>
          </Box>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/parser" element={<Parser />} />
        </Routes>
      </Container>

      <Box 
        component="footer" 
        sx={{ 
          py: 3, 
          px: 2, 
          mt: 'auto', 
          backgroundColor: (theme) => theme.palette.grey[100],
          borderTop: 1,
          borderColor: 'divider'
        }}
      >
        <Container maxWidth="lg">
          <Typography variant="body2" color="text.secondary" align="center">
            © {new Date().getFullYear()} Обработчик файлов. Все права защищены.
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center">
            Система обработки UCA и УльтраЗвук файлов
          </Typography>
        </Container>
      </Box>
    </React.Fragment>
  )
}

export default App