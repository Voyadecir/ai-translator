"""
UI Translation Module - Context-Aware Interface Translation
Translates UI elements (buttons, menus, labels) with proper context

Problem: "Uploads" → "Cargas" (technically correct, but users don't understand)
Solution: "Uploads" → "Subir archivos" or "Cómo subir un documento" (action-oriented)

This module understands:
- UI element types (button, menu, label, error message)
- User intent (what action will this trigger?)
- Platform conventions (how does this platform typically phrase things?)
"""

from typing import Dict, List, Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class UITranslation:
    """
    Context-aware UI element translation
    
    Features:
    - Element-type awareness (button, menu, label, etc.)
    - Action-oriented phrasing
    - Platform conventions (web, mobile, desktop)
    - Consistency across interface
    - User-friendly language (not technical jargon)
    """
    
    def __init__(self):
        # Load UI-specific translation mappings
        self.ui_mappings = self._load_ui_mappings()
        self.action_verbs = self._load_action_verbs()
        self.platform_conventions = self._load_platform_conventions()
    
    # ============================================================================
    # UI TRANSLATION MAPPINGS (Context-Aware)
    # ============================================================================
    
    def _load_ui_mappings(self) -> Dict[str, Dict]:
        """
        UI element translations with context
        
        Key: english_term
        Value: {
            'element_type': {
                'translation': spanish_translation,
                'user_friendly': alternative_phrasing,
                'context': when_to_use
            }
        }
        """
        return {
            # FILE OPERATIONS
            "upload": {
                "button": {
                    "es": "Subir",
                    "user_friendly": "Subir archivo",
                    "icon_text": "📤 Subir",
                    "context": "Action button to upload files"
                },
                "menu": {
                    "es": "Subir archivos",
                    "user_friendly": "Cómo subir un documento",
                    "help_text": "Subir documentos",
                    "context": "Menu item or navigation"
                },
                "heading": {
                    "es": "Subir archivo",
                    "user_friendly": "Sube tu documento",
                    "context": "Page heading"
                },
                "gerund": {
                    "es": "Subiendo...",
                    "user_friendly": "Subiendo tu archivo...",
                    "context": "Progress indicator"
                }
            },
            
            "uploads": {
                "menu": {
                    "es": "Subir archivos",
                    "user_friendly": "Cómo subir documentos",
                    "help_text": "Ver cómo subir archivos",
                    "context": "Menu/navigation - plural form"
                },
                "section": {
                    "es": "Archivos subidos",
                    "user_friendly": "Tus documentos",
                    "context": "Section showing uploaded files"
                }
            },
            
            "download": {
                "button": {
                    "es": "Descargar",
                    "user_friendly": "Descargar archivo",
                    "icon_text": "⬇️ Descargar",
                    "context": "Download action"
                },
                "menu": {
                    "es": "Descargas",
                    "user_friendly": "Mis descargas",
                    "context": "Downloads section"
                }
            },
            
            "delete": {
                "button": {
                    "es": "Eliminar",
                    "user_friendly": "Borrar",
                    "warning": "¿Eliminar este archivo?",
                    "context": "Delete action"
                },
                "confirmation": {
                    "es": "¿Estás seguro?",
                    "user_friendly": "¿Quieres eliminar esto?",
                    "context": "Confirmation dialog"
                }
            },
            
            # NAVIGATION
            "home": {
                "menu": {
                    "es": "Inicio",
                    "user_friendly": "Página principal",
                    "icon_text": "🏠 Inicio",
                    "context": "Home/main page"
                }
            },
            
            "back": {
                "button": {
                    "es": "Volver",
                    "user_friendly": "Regresar",
                    "icon_text": "← Volver",
                    "context": "Go back action"
                }
            },
            
            "next": {
                "button": {
                    "es": "Siguiente",
                    "user_friendly": "Continuar",
                    "context": "Next step/page"
                }
            },
            
            "previous": {
                "button": {
                    "es": "Anterior",
                    "user_friendly": "Atrás",
                    "icon_text": "← Anterior",
                    "context": "Previous page"
                }
            },
            
            # USER ACTIONS
            "save": {
                "button": {
                    "es": "Guardar",
                    "user_friendly": "Guardar cambios",
                    "confirmation": "Guardado ✓",
                    "context": "Save action"
                },
                "auto_save": {
                    "es": "Guardado automático",
                    "user_friendly": "Se guardó automáticamente",
                    "context": "Auto-save indicator"
                }
            },
            
            "cancel": {
                "button": {
                    "es": "Cancelar",
                    "user_friendly": "No, cancelar",
                    "context": "Cancel action"
                }
            },
            
            "submit": {
                "button": {
                    "es": "Enviar",
                    "user_friendly": "Enviar formulario",
                    "form_context": "Completar",
                    "context": "Submit form"
                }
            },
            
            "edit": {
                "button": {
                    "es": "Editar",
                    "user_friendly": "Modificar",
                    "icon_text": "✏️ Editar",
                    "context": "Edit action"
                }
            },
            
            # ACCOUNT/SETTINGS
            "login": {
                "button": {
                    "es": "Iniciar sesión",
                    "user_friendly": "Entrar",
                    "context": "Login action"
                },
                "heading": {
                    "es": "Iniciar sesión",
                    "user_friendly": "Ingresa a tu cuenta",
                    "context": "Login page heading"
                }
            },
            
            "logout": {
                "button": {
                    "es": "Cerrar sesión",
                    "user_friendly": "Salir",
                    "context": "Logout action"
                }
            },
            
            "settings": {
                "menu": {
                    "es": "Configuración",
                    "user_friendly": "Ajustes",
                    "icon_text": "⚙️ Configuración",
                    "context": "Settings menu"
                }
            },
            
            "profile": {
                "menu": {
                    "es": "Perfil",
                    "user_friendly": "Mi perfil",
                    "context": "User profile"
                }
            },
            
            # STATUS/FEEDBACK
            "loading": {
                "status": {
                    "es": "Cargando...",
                    "user_friendly": "Un momento...",
                    "context": "Loading indicator"
                }
            },
            
            "error": {
                "heading": {
                    "es": "Error",
                    "user_friendly": "Algo salió mal",
                    "context": "Error message"
                }
            },
            
            "success": {
                "message": {
                    "es": "Éxito",
                    "user_friendly": "¡Listo!",
                    "confirmation": "✓ Completado",
                    "context": "Success message"
                }
            },
            
            # HELP/SUPPORT
            "help": {
                "menu": {
                    "es": "Ayuda",
                    "user_friendly": "¿Necesitas ayuda?",
                    "icon_text": "❓ Ayuda",
                    "context": "Help section"
                },
                "button": {
                    "es": "Ayuda",
                    "user_friendly": "Ver ayuda",
                    "context": "Help button"
                }
            },
            
            "support": {
                "menu": {
                    "es": "Soporte",
                    "user_friendly": "Centro de ayuda",
                    "context": "Support center"
                }
            },
            
            "faq": {
                "menu": {
                    "es": "Preguntas frecuentes",
                    "user_friendly": "Preguntas comunes",
                    "abbreviation": "FAQ",
                    "context": "FAQ section"
                }
            },
            
            # SEARCH/FILTER
            "search": {
                "button": {
                    "es": "Buscar",
                    "user_friendly": "Buscar",
                    "icon_text": "🔍 Buscar",
                    "context": "Search action"
                },
                "placeholder": {
                    "es": "Buscar...",
                    "user_friendly": "¿Qué buscas?",
                    "context": "Search input placeholder"
                }
            },
            
            "filter": {
                "button": {
                    "es": "Filtrar",
                    "user_friendly": "Filtros",
                    "context": "Filter action"
                }
            },
            
            # Add 200+ more UI terms...
        }
    
    def _load_action_verbs(self) -> Dict[str, str]:
        """
        Action verbs for user-facing buttons
        
        English verb → Spanish imperative (command form)
        """
        return {
            "click": "Haz clic",
            "tap": "Toca",
            "press": "Presiona",
            "select": "Selecciona",
            "choose": "Elige",
            "open": "Abre",
            "close": "Cierra",
            "view": "Ver",
            "show": "Mostrar",
            "hide": "Ocultar",
            "copy": "Copiar",
            "paste": "Pegar",
            "share": "Compartir",
            "print": "Imprimir",
            "refresh": "Actualizar",
            "reload": "Recargar",
        }
    
    def _load_platform_conventions(self) -> Dict[str, Dict]:
        """
        Platform-specific phrasing conventions
        """
        return {
            "web": {
                "upload": "Subir archivo",
                "download": "Descargar",
                "click": "Haz clic en",
            },
            "mobile": {
                "upload": "Subir foto",
                "download": "Descargar",
                "click": "Toca",
            },
            "desktop": {
                "upload": "Seleccionar archivo",
                "download": "Guardar en equipo",
                "click": "Haz clic en",
            }
        }
    
    # ============================================================================
    # MAIN TRANSLATION METHOD
    # ============================================================================
    
    @lru_cache(maxsize=1000)
    def translate_ui_element(self,
                            text: str,
                            element_type: str = "button",
                            context: Optional[str] = None,
                            platform: str = "web",
                            target_lang: str = "es") -> str:
        """
        Translate UI element with proper context
        
        Args:
            text: English UI text (e.g., "upload", "uploads", "save")
            element_type: Type of UI element (button, menu, label, heading, etc.)
            context: Optional context (e.g., "file_upload", "navigation")
            platform: Platform type (web, mobile, desktop)
            target_lang: Target language (es, pt, fr)
        
        Returns:
            Context-appropriate translation
        
        Examples:
            translate_ui_element("upload", "button") → "Subir"
            translate_ui_element("upload", "menu") → "Subir archivos"
            translate_ui_element("uploads", "menu") → "Cómo subir documentos"
        """
        text_lower = text.lower().strip()
        
        # Check if we have a mapping for this term
        if text_lower in self.ui_mappings:
            term_data = self.ui_mappings[text_lower]
            
            # Get element-type specific translation
            if element_type in term_data:
                element_data = term_data[element_type]
                
                # Return user-friendly version by default
                if target_lang in element_data:
                    return element_data[target_lang]
                elif 'user_friendly' in element_data:
                    return element_data['user_friendly']
                elif 'es' in element_data:  # Fallback to standard Spanish
                    return element_data['es']
            
            # Fallback: try to find any translation
            for elem_type, elem_data in term_data.items():
                if target_lang in elem_data:
                    return elem_data[target_lang]
                elif 'user_friendly' in elem_data:
                    return elem_data['user_friendly']
        
        # If no mapping found, return original (log warning)
        logger.warning(f"No UI translation found for: '{text}' ({element_type})")
        return text
    
    def translate_ui_batch(self, 
                          ui_elements: List[Dict],
                          target_lang: str = "es") -> List[Dict]:
        """
        Translate multiple UI elements at once
        
        Args:
            ui_elements: List of dicts with {text, element_type, context}
            target_lang: Target language
        
        Returns:
            List of dicts with translations added
        """
        results = []
        
        for element in ui_elements:
            text = element.get('text', '')
            element_type = element.get('element_type', 'button')
            context = element.get('context')
            platform = element.get('platform', 'web')
            
            translation = self.translate_ui_element(
                text, element_type, context, platform, target_lang
            )
            
            results.append({
                **element,
                'translation': translation
            })
        
        return results
    
    def get_help_text(self, 
                     action: str,
                     target_lang: str = "es") -> str:
        """
        Generate helpful explanatory text for actions
        
        Args:
            action: Action name (e.g., "upload", "download")
            target_lang: Target language
        
        Returns:
            User-friendly help text
        
        Example:
            get_help_text("upload") → "Cómo subir un documento: Haz clic en 'Subir' y selecciona el archivo"
        """
        action_lower = action.lower()
        
        help_texts = {
            "upload": {
                "es": "Cómo subir un documento: Haz clic en 'Subir' y selecciona el archivo de tu computadora",
                "short": "Sube archivos desde tu dispositivo"
            },
            "download": {
                "es": "Cómo descargar: Haz clic en 'Descargar' para guardar el archivo en tu dispositivo",
                "short": "Guarda archivos en tu dispositivo"
            },
            "translate": {
                "es": "Cómo traducir: Selecciona el idioma y haz clic en 'Traducir'",
                "short": "Convierte texto a otro idioma"
            },
            "delete": {
                "es": "Cómo eliminar: Haz clic en 'Eliminar' y confirma la acción",
                "short": "Borra archivos permanentemente"
            }
        }
        
        if action_lower in help_texts:
            return help_texts[action_lower].get(target_lang, help_texts[action_lower].get('short', ''))
        
        return f"Ayuda para: {action}"


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
ui_translator = UITranslation()

# Convenience functions
def translate_button(text: str, target_lang: str = "es") -> str:
    """Translate button text"""
    return ui_translator.translate_ui_element(text, "button", target_lang=target_lang)

def translate_menu(text: str, target_lang: str = "es") -> str:
    """Translate menu item"""
    return ui_translator.translate_ui_element(text, "menu", target_lang=target_lang)

def translate_label(text: str, target_lang: str = "es") -> str:
    """Translate label/heading"""
    return ui_translator.translate_ui_element(text, "label", target_lang=target_lang)


# Test example
if __name__ == "__main__":
    print("\n" + "="*60)
    print("UI TRANSLATION - CONTEXT-AWARE INTERFACE TRANSLATION")
    print("="*60)
    
    # Your real-world example
    print("\n**YOUR EXAMPLE: 'uploads'**")
    print(f"As button: {translate_button('upload')}")
    print(f"As menu: {translate_menu('uploads')}")
    print(f"Help text: {ui_translator.get_help_text('upload')}")
    
    # More examples
    print("\n**OTHER UI ELEMENTS:**")
    print(f"Save (button): {translate_button('save')}")
    print(f"Settings (menu): {translate_menu('settings')}")
    print(f"Login (button): {translate_button('login')}")
    print(f"Help (menu): {translate_menu('help')}")
    
    print("\n" + "="*60)
