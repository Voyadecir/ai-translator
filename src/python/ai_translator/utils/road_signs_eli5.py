"""
Road Signs ELI5 - Traffic Sign Translations with Simple Explanations
Translates road signs AND explains what they mean in simple language
Critical for immigrants who need to understand US traffic laws

Philosophy: Don't just translate "YIELD" → "CEDA EL PASO"
Explain: "YIELD = Slow down and let other cars go first. Stop if needed."

This saves lives. New immigrants MUST understand traffic signs.
"""

import re
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

class RoadSignsELI5:
    """
    Translates and explains road signs in simple language
    
    Key Features:
    - Translate sign text to target language
    - ELI5 explanation (Explain Like I'm 5)
    - What to do (action steps)
    - Legal consequences of ignoring
    - Regional variations
    - Visual description (color, shape)
    
    Coverage:
    - US road signs (federal standards)
    - State-specific signs
    - Parking signs
    - Highway signs
    - Construction signs
    - Warning signs
    """
    
    def __init__(self):
        # Road sign databases
        self.regulatory_signs = self._load_regulatory_signs()
        self.warning_signs = self._load_warning_signs()
        self.guide_signs = self._load_guide_signs()
        self.parking_signs = self._load_parking_signs()
        self.construction_signs = self._load_construction_signs()
        
       
    
    # ============================================================================
    # REGULATORY SIGNS (Must obey - laws)
    # ============================================================================
    
    def _load_regulatory_signs(self) -> Dict[str, Dict]:
        """
        Regulatory signs - these are LAWS you must follow
        """
        return {
            "STOP": {
                "category": "regulatory",
                "visual": {
                    "shape": "Octagon (8 sides)",
                    "color": "Red background, white letters",
                    "unique": "Only sign with 8 sides - recognize by shape alone"
                },
                "es": {
                    "translation": "ALTO",
                    "eli5": "Detente completamente. El carro debe dejar de moverse por completo.",
                    "what_to_do": [
                        "1. Detén tu carro COMPLETAMENTE (velocidad = 0)",
                        "2. Para en la línea blanca o antes del cruce",
                        "3. Mira a la izquierda, derecha, izquierda otra vez",
                        "4. Espera hasta que sea seguro",
                        "5. Luego puedes seguir"
                    ],
                    "common_mistake": "⚠️ 'Rolling stop' (rodar sin parar) es ILEGAL. Debes parar completamente.",
                    "penalty": "Multa $100-500, puntos en licencia, posible aumento en seguro"
                },
                "pt": {
                    "translation": "PARE",
                    "eli5": "Pare completamente. O carro deve parar de se mover.",
                    "what_to_do": [
                        "1. Pare seu carro COMPLETAMENTE (velocidade = 0)",
                        "2. Pare na linha branca ou antes do cruzamento",
                        "3. Olhe à esquerda, direita, esquerda novamente",
                        "4. Espere até que seja seguro",
                        "5. Depois pode continuar"
                    ]
                },
                "legal_note": "Federal requirement - must come to COMPLETE stop",
                "explanation_en": "You MUST stop completely. The car must reach 0 mph. Look both ways. Then you can go when safe."
            },
            
            "YIELD": {
                "category": "regulatory",
                "visual": {
                    "shape": "Inverted triangle (point down)",
                    "color": "Red border, white background",
                    "unique": "Only inverted triangle sign"
                },
                "es": {
                    "translation": "CEDA EL PASO",
                    "eli5": "Permite que otros carros pasen primero. Baja la velocidad y estate listo para parar.",
                    "what_to_do": [
                        "1. Reduce la velocidad",
                        "2. Revisa si vienen otros carros",
                        "3. Si viene alguien, PARA y déjalos pasar primero",
                        "4. Si NO viene nadie, puedes continuar sin parar",
                        "5. Los otros carros tienen prioridad (van primero)"
                    ],
                    "common_mistake": "⚠️ YIELD no significa 'para siempre'. Si no viene nadie, puedes seguir.",
                    "vs_stop": "DIFERENCIA: STOP = siempre parar. YIELD = parar solo si viene alguien.",
                    "penalty": "Multa $100-400 si no cedes el paso"
                },
                "pt": {
                    "translation": "DÊ A PREFERÊNCIA",
                    "eli5": "Deixe outros carros passarem primeiro. Reduza a velocidade e esteja pronto para parar.",
                    "what_to_do": [
                        "1. Reduza a velocidade",
                        "2. Verifique se há outros carros",
                        "3. Se houver alguém, PARE e deixe passar primeiro",
                        "4. Se NÃO houver ninguém, pode continuar sem parar",
                        "5. Os outros carros têm prioridade"
                    ]
                },
                "explanation_en": "Slow down. Let other cars go first. Stop if needed. If no one is coming, you can keep going."
            },
            
            "SPEED LIMIT 55": {
                "category": "regulatory",
                "visual": {
                    "shape": "Rectangle (vertical)",
                    "color": "White background, black letters"
                },
                "es": {
                    "translation": "LÍMITE DE VELOCIDAD 55",
                    "eli5": "La velocidad máxima permitida es 55 millas por hora. No puedes ir más rápido que esto.",
                    "what_to_do": [
                        "1. Mira tu velocímetro (donde dice la velocidad)",
                        "2. Asegúrate de que no muestre más de 55",
                        "3. Si vas a 60 o más, reduce la velocidad",
                        "4. Esta es la velocidad MÁXIMA - puedes ir más lento si quieres"
                    ],
                    "mph_to_kmh": "55 mph = aproximadamente 88 km/h",
                    "penalty": "Multa $100-1000 dependiendo de cuánto excedas el límite",
                    "insurance_impact": "Multas de velocidad suben el costo de tu seguro"
                },
                "pt": {
                    "translation": "LIMITE DE VELOCIDADE 55",
                    "eli5": "A velocidade máxima permitida é 55 milhas por hora. Você não pode ir mais rápido que isso.",
                    "what_to_do": [
                        "1. Olhe seu velocímetro",
                        "2. Certifique-se de que não mostre mais de 55",
                        "3. Se estiver a 60 ou mais, reduza a velocidade"
                    ]
                },
                "explanation_en": "Maximum speed allowed is 55 mph. You cannot go faster than this. Look at your speedometer."
            },
            
            "DO NOT ENTER": {
                "category": "regulatory",
                "visual": {
                    "shape": "Square/Rectangle",
                    "color": "Red background, white letters",
                    "icon": "Often has white horizontal bar"
                },
                "es": {
                    "translation": "NO ENTRE / PROHIBIDO ENTRAR",
                    "eli5": "¡NO puedes entrar aquí! Esta calle va en la otra dirección. Si entras, chocarás con carros que vienen de frente.",
                    "what_to_do": [
                        "1. ¡NO ENTRES! Busca otra ruta",
                        "2. Este letrero está en calles de un solo sentido",
                        "3. Los carros vienen hacia ti en esta dirección",
                        "4. Entrar aquí es MUY PELIGROSO y ilegal"
                    ],
                    "common_location": "Rampas de salida de autopistas, calles de una sola vía",
                    "danger_level": "🔴 CRÍTICO - Puede causar accidente frontal (choque de frente)",
                    "penalty": "Multa $200-1000, puntos en licencia, posible arresto"
                },
                "pt": {
                    "translation": "NÃO ENTRE / PROIBIDO ENTRAR",
                    "eli5": "Você NÃO pode entrar aqui! Esta rua vai na outra direção.",
                    "danger_level": "🔴 CRÍTICO - Pode causar acidente frontal"
                },
                "explanation_en": "DO NOT ENTER HERE. This road goes the opposite direction. You will hit oncoming traffic. Very dangerous!"
            },
            
            "WRONG WAY": {
                "category": "regulatory",
                "visual": {
                    "shape": "Rectangle (horizontal)",
                    "color": "Red background, white letters",
                    "size": "Large letters"
                },
                "es": {
                    "translation": "DIRECCIÓN INCORRECTA / VÍA EQUIVOCADA",
                    "eli5": "¡Estás yendo en la dirección equivocada! DA LA VUELTA INMEDIATAMENTE antes de chocar.",
                    "what_to_do": [
                        "1. ¡PARA INMEDIATAMENTE!",
                        "2. Enciende las luces de emergencia (hazard lights)",
                        "3. Busca un lugar seguro para dar la vuelta",
                        "4. Regresa y busca la entrada correcta",
                        "5. Si es autopista, sal lo antes posible"
                    ],
                    "emergency": "Si ves este letrero, ¡ya entraste mal! Actúa rápido.",
                    "danger_level": "🔴 EMERGENCIA - Riesgo de muerte",
                    "penalty": "Multa muy alta, suspensión de licencia posible"
                },
                "pt": {
                    "translation": "DIREÇÃO ERRADA / VIA ERRADA",
                    "eli5": "Você está indo na direção errada! DÊ A VOLTA IMEDIATAMENTE.",
                    "danger_level": "🔴 EMERGÊNCIA - Risco de morte"
                },
                "explanation_en": "You are going the WRONG WAY! Turn around immediately! You are driving into oncoming traffic!"
            },
            
            "ONE WAY": {
                "category": "regulatory",
                "visual": {
                    "shape": "Rectangle (horizontal)",
                    "color": "Black background, white letters and arrow",
                    "arrow": "Points in direction of travel"
                },
                "es": {
                    "translation": "UNA SOLA VÍA / UN SOLO SENTIDO",
                    "eli5": "Todos los carros van en UNA dirección solamente (la dirección de la flecha).",
                    "what_to_do": [
                        "1. Solo puedes ir en la dirección de la flecha",
                        "2. NO puedes dar vuelta para ir en contra",
                        "3. Todos los carros van en la misma dirección",
                        "4. Para salir, busca otra calle"
                    ],
                    "arrow_meaning": "La flecha muestra la ÚNICA dirección permitida",
                    "penalty": "Ir en dirección contraria = multa $200-800"
                },
                "pt": {
                    "translation": "MÃO ÚNICA / UMA VIA",
                    "eli5": "Todos os carros vão em UMA direção apenas (direção da seta).",
                    "what_to_do": [
                        "1. Você só pode ir na direção da seta",
                        "2. NÃO pode virar para ir contra"
                    ]
                },
                "explanation_en": "All cars go ONE direction only (direction of arrow). You cannot turn around."
            },
            
            "NO U-TURN": {
                "category": "regulatory",
                "visual": {
                    "shape": "Circle",
                    "color": "White background, red circle with slash",
                    "icon": "U-turn arrow with red slash through it"
                },
                "es": {
                    "translation": "PROHIBIDO DAR VUELTA EN U",
                    "eli5": "No puedes dar la vuelta completa (180 grados) aquí. Busca otro lugar para voltear.",
                    "what_to_do": [
                        "1. NO hagas una vuelta en U en este lugar",
                        "2. Sigue derecho o dobla en una esquina",
                        "3. Busca un lugar donde SÍ esté permitido voltear",
                        "4. O da la vuelta en una manzana (cuadra completa)"
                    ],
                    "common_location": "Intersecciones ocupadas, cerca de escuelas, autopistas",
                    "penalty": "Multa $100-400"
                },
                "pt": {
                    "translation": "PROIBIDO RETORNO",
                    "eli5": "Você não pode dar meia-volta (180 graus) aqui.",
                    "penalty": "Multa $100-400"
                },
                "explanation_en": "You cannot make a U-turn here (turn around 180 degrees). Find another place to turn around."
            },
            
            "NO LEFT TURN": {
                "category": "regulatory",
                "visual": {
                    "shape": "Circle",
                    "color": "White background, red circle with slash",
                    "icon": "Left arrow with red slash"
                },
                "es": {
                    "translation": "PROHIBIDO DOBLAR A LA IZQUIERDA",
                    "eli5": "No puedes voltear a la izquierda en esta esquina. Solo puedes seguir derecho o voltear a la derecha.",
                    "what_to_do": [
                        "1. NO voltees a la izquierda",
                        "2. Sigue derecho o dobla a la derecha",
                        "3. Para ir a la izquierda, busca otra calle"
                    ],
                    "penalty": "Multa $100-300"
                },
                "pt": {
                    "translation": "PROIBIDO VIRAR À ESQUERDA",
                    "eli5": "Você não pode virar à esquerda neste cruzamento."
                },
                "explanation_en": "You cannot turn left at this intersection. Go straight or turn right only."
            },
            
            "NO RIGHT TURN": {
                "category": "regulatory",
                "visual": {
                    "shape": "Circle",
                    "color": "White background, red circle with slash",
                    "icon": "Right arrow with red slash"
                },
                "es": {
                    "translation": "PROHIBIDO DOBLAR A LA DERECHA",
                    "eli5": "No puedes voltear a la derecha en esta esquina.",
                    "what_to_do": [
                        "1. NO voltees a la derecha",
                        "2. Sigue derecho o dobla a la izquierda"
                    ],
                    "penalty": "Multa $100-300"
                },
                "explanation_en": "You cannot turn right at this intersection. Go straight or turn left only."
            },
            
            "NO PARKING ANYTIME": {
                "category": "regulatory",
                "visual": {
                    "shape": "Rectangle (vertical)",
                    "color": "White background, red letters or red background"
                },
                "es": {
                    "translation": "PROHIBIDO ESTACIONARSE EN CUALQUIER MOMENTO",
                    "eli5": "NUNCA puedes estacionar tu carro aquí. Ni por un minuto. Ni de día ni de noche.",
                    "what_to_do": [
                        "1. NO estaciones aquí NUNCA",
                        "2. Ni siquiera para dejar a alguien rápido",
                        "3. Tu carro será remolcado (tow truck se lo lleva)",
                        "4. Busca estacionamiento permitido"
                    ],
                    "penalty": "Multa $50-500 + cargo de remolque $200-400 = TOTAL $250-900",
                    "tow_warning": "⚠️ Tu carro será remolcado. Tendrás que pagar para recuperarlo."
                },
                "pt": {
                    "translation": "PROIBIDO ESTACIONAR A QUALQUER MOMENTO",
                    "eli5": "NUNCA pode estacionar seu carro aqui.",
                    "penalty": "Multa + reboque = $250-900"
                },
                "explanation_en": "You can NEVER park here. Not even for 1 minute. Your car will be towed."
            },
            
            # Add 100+ more regulatory signs...
        }
    
    # ============================================================================
    # WARNING SIGNS (Alerts to hazards)
    # ============================================================================
    
    def _load_warning_signs(self) -> Dict[str, Dict]:
        """
        Warning signs - alert you to dangers ahead
        """
        return {
            "SCHOOL ZONE": {
                "category": "warning",
                "visual": {
                    "shape": "Pentagon (5 sides) or Rectangle",
                    "color": "Fluorescent yellow-green background, black letters",
                    "unique": "Bright fluorescent color"
                },
                "es": {
                    "translation": "ZONA ESCOLAR",
                    "eli5": "Hay una escuela cerca. Muchos niños cruzan la calle aquí. Ve MUY despacio.",
                    "what_to_do": [
                        "1. Reduce la velocidad a 15-25 mph",
                        "2. Busca niños cruzando la calle",
                        "3. Estate listo para parar en cualquier momento",
                        "4. NO uses el teléfono",
                        "5. Ten cuidado EXTRA durante horas de escuela (7-9am, 2-4pm)"
                    ],
                    "speed_limit": "Usualmente 15-25 mph durante horas de escuela",
                    "penalty": "Multas DOBLES en zonas escolares. Exceso de velocidad = $200-1000",
                    "danger": "Los niños pueden cruzar sin mirar. ¡Ve DESPACIO!"
                },
                "pt": {
                    "translation": "ZONA ESCOLAR",
                    "eli5": "Há uma escola perto. Muitas crianças cruzam a rua aqui. Vá MUITO devagar.",
                    "speed_limit": "Geralmente 15-25 mph durante horário escolar"
                },
                "explanation_en": "School nearby. Many children cross here. Slow down to 15-25 mph. Watch for kids!"
            },
            
            "PEDESTRIAN CROSSING": {
                "category": "warning",
                "visual": {
                    "shape": "Diamond",
                    "color": "Yellow background, black icon of person walking"
                },
                "es": {
                    "translation": "CRUCE DE PEATONES",
                    "eli5": "Las personas cruzan la calle aquí. Estate listo para parar si ves a alguien.",
                    "what_to_do": [
                        "1. Reduce la velocidad",
                        "2. Busca personas esperando para cruzar",
                        "3. Si alguien está en el cruce, PARA completamente",
                        "4. Espera hasta que crucen completamente",
                        "5. Los peatones SIEMPRE tienen el derecho de paso"
                    ],
                    "law": "Es ILEGAL no parar para peatones en el cruce",
                    "penalty": "Multa $100-500, puntos en licencia"
                },
                "pt": {
                    "translation": "TRAVESSIA DE PEDESTRES",
                    "eli5": "Pessoas cruzam a rua aqui. Esteja pronto para parar.",
                    "law": "É ILEGAL não parar para pedestres na faixa"
                },
                "explanation_en": "People cross the street here. Slow down. STOP if someone is in crosswalk. Pedestrians have right of way."
            },
            
            "RAILROAD CROSSING": {
                "category": "warning",
                "visual": {
                    "shape": "Circle (yellow) or X-shaped sign (white)",
                    "color": "Yellow with X symbol, or white X with 'RR'",
                    "additional": "Often has flashing lights and gates"
                },
                "es": {
                    "translation": "CRUCE DE FERROCARRIL / CRUCE DE TREN",
                    "eli5": "Las vías del tren cruzan la calle aquí. PARA completamente antes de las vías.",
                    "what_to_do": [
                        "1. Reduce la velocidad al acercarte",
                        "2. PARA completamente antes de las vías",
                        "3. Mira a ambos lados - izquierda y derecha",
                        "4. Escucha si viene un tren",
                        "5. Si las luces parpadean o la barrera baja, ESPERA",
                        "6. NUNCA cruces si las luces parpadean",
                        "7. Cruza solo cuando sea completamente seguro"
                    ],
                    "flashing_lights": "🔴 Luces parpadeando = TREN VIENE. NO CRUCES.",
                    "gates_down": "🔴 Barreras bajadas = TREN VIENE. ESPERA.",
                    "danger_level": "🔴 EXTREMO - Los trenes no pueden parar rápido",
                    "penalty": "Multa $500-1000 + suspensión de licencia. Cruzar cuando viene tren = posible muerte"
                },
                "pt": {
                    "translation": "PASSAGEM DE TREM",
                    "eli5": "Trilhos de trem cruzam a rua aqui. PARE completamente antes dos trilhos.",
                    "danger_level": "🔴 EXTREMO - Trens não podem parar rápido"
                },
                "explanation_en": "Train tracks cross road here. STOP completely before tracks. Look and listen for trains. NEVER cross when lights are flashing."
            },
            
            "DEER CROSSING": {
                "category": "warning",
                "visual": {
                    "shape": "Diamond",
                    "color": "Yellow background, black silhouette of deer"
                },
                "es": {
                    "translation": "CRUCE DE VENADOS",
                    "eli5": "Los venados (animales grandes) cruzan la calle aquí. Ve despacio, especialmente de noche.",
                    "what_to_do": [
                        "1. Reduce la velocidad",
                        "2. Estate alerta, especialmente al amanecer y al anochecer",
                        "3. Si ves un venado, probablemente hay más cerca",
                        "4. Si un venado cruza, NO hagas una vuelta brusca",
                        "5. Es mejor chocar con el venado que salirte del camino"
                    ],
                    "night_danger": "⚠️ Los venados son más activos de noche. Difíciles de ver.",
                    "insurance_note": "Chocar con venado generalmente está cubierto por seguro comprehensive"
                },
                "pt": {
                    "translation": "TRAVESSIA DE VEADOS",
                    "eli5": "Veados (animais grandes) cruzam a estrada aqui. Vá devagar.",
                    "night_danger": "⚠️ Veados são mais ativos à noite"
                },
                "explanation_en": "Deer cross road here. Slow down, especially at night. If you see one deer, there are probably more nearby."
            },
            
            "SLIPPERY WHEN WET": {
                "category": "warning",
                "visual": {
                    "shape": "Diamond",
                    "color": "Yellow background, black car sliding icon"
                },
                "es": {
                    "translation": "RESBALOSO CUANDO MOJADO",
                    "eli5": "Cuando llueve, esta calle se pone muy resbalosa. Tu carro puede deslizarse.",
                    "what_to_do": [
                        "1. Cuando llueve, ve más despacio aquí",
                        "2. No frenes (pares) de repente",
                        "3. Mantén más distancia con el carro de enfrente",
                        "4. Dobla suavemente (no brusco)",
                        "5. Si el carro se desliza, no entres en pánico"
                    ],
                    "rain_tip": "En lluvia, reduce velocidad en 10-15 mph",
                    "danger": "Riesgo de derrapar (skid) o perder control"
                },
                "pt": {
                    "translation": "ESCORREGADIO QUANDO MOLHADO",
                    "eli5": "Quando chove, esta rua fica muito escorregadia. Seu carro pode deslizar.",
                    "danger": "Risco de derrapar ou perder controle"
                },
                "explanation_en": "Road is very slippery when it rains. Your car can slide. Slow down in rain. Don't brake suddenly."
            },
            
            # Add 50+ more warning signs...
        }
    
    # ============================================================================
    # GUIDE SIGNS (Directions and information)
    # ============================================================================
    
    def _load_guide_signs(self) -> Dict[str, Dict]:
        """
        Guide signs - give directions and information
        """
        return {
            "INTERSTATE [number]": {
                "category": "guide",
                "visual": {
                    "shape": "Shield",
                    "color": "Red, white, and blue shield shape",
                    "numbering": "Even numbers = East-West, Odd numbers = North-South"
                },
                "es": {
                    "translation": "AUTOPISTA INTERESTATAL [número]",
                    "eli5": "Esta es una autopista grande que conecta estados. Los números pares (2,4,6) van Este-Oeste. Los números impares (1,3,5) van Norte-Sur.",
                    "numbering_system": {
                        "even": "Números pares (I-10, I-40, I-80) = van Este-Oeste",
                        "odd": "Números impares (I-5, I-95) = van Norte-Sur",
                        "three_digit": "Tres dígitos (I-405, I-280) = carretera alrededor de ciudad"
                    }
                },
                "explanation_en": "Major highway connecting states. Even numbers go East-West. Odd numbers go North-South."
            },
            
            "EXIT [number]": {
                "category": "guide",
                "visual": {
                    "shape": "Rectangle",
                    "color": "Green background, white letters (on highway)"
                },
                "es": {
                    "translation": "SALIDA [número]",
                    "eli5": "Esta es la salida de la autopista. Cambia de carril a la derecha para salir.",
                    "what_to_do": [
                        "1. Enciende tu señal direccional (blinker) a la derecha",
                        "2. Cambia de carril hacia la derecha",
                        "3. Reduce la velocidad en la rampa de salida",
                        "4. Sigue las señales después de salir"
                    ],
                    "miss_exit": "Si te pasas la salida, toma la siguiente. NO des reversa en autopista."
                },
                "explanation_en": "Highway exit. Turn on right signal. Move to right lane. Slow down on exit ramp."
            },
            
            # Add 30+ more guide signs...
        }
    
    # ============================================================================
    # PARKING SIGNS
    # ============================================================================
    
    def _load_parking_signs(self) -> Dict[str, Dict]:
        """
        Parking regulation signs
        """
        return {
            "2 HOUR PARKING 8AM-6PM MON-FRI": {
                "category": "parking",
                "visual": {
                    "shape": "Rectangle (vertical)",
                    "color": "Green background (time limit) or White background"
                },
                "es": {
                    "translation": "ESTACIONAMIENTO DE 2 HORAS 8AM-6PM LUN-VIE",
                    "eli5": "Puedes estacionarte aquí por MÁXIMO 2 horas, pero solo de lunes a viernes entre 8am y 6pm.",
                    "what_to_do": [
                        "1. Puedes estacionarte MÁXIMO 2 horas",
                        "2. Esto aplica de Lunes a Viernes",
                        "3. Solo entre 8am y 6pm",
                        "4. Después de 6pm = estacionamiento gratis sin límite",
                        "5. Sábado y Domingo = estacionamiento gratis sin límite",
                        "6. Pon una nota con la hora en que llegaste (opcional pero ayuda)"
                    ],
                    "penalty": "Si te pasas de 2 horas = multa $25-75",
                    "weekend": "Fines de semana y después de 6pm = SIN límite de tiempo"
                },
                "explanation_en": "You can park for MAXIMUM 2 hours, Monday-Friday between 8am-6pm. Free parking after 6pm and on weekends."
            },
            
            # Add 40+ more parking signs...
        }
    
    # ============================================================================
    # CONSTRUCTION SIGNS
    # ============================================================================
    
    def _load_construction_signs(self) -> Dict[str, Dict]:
        """
        Construction and work zone signs
        """
        return {
            "ROAD WORK AHEAD": {
                "category": "construction",
                "visual": {
                    "shape": "Diamond",
                    "color": "Orange background, black letters",
                    "unique": "Orange = construction/work zone"
                },
                "es": {
                    "translation": "TRABAJO EN LA CALLE ADELANTE",
                    "eli5": "Hay trabajadores arreglando la calle más adelante. Ve despacio y ten cuidado.",
                    "what_to_do": [
                        "1. Reduce la velocidad",
                        "2. Estate listo para parar",
                        "3. Busca trabajadores en la calle",
                        "4. Sigue los letreros naranjas",
                        "5. Ten paciencia - puede haber retrasos"
                    ],
                    "penalty": "Multas DOBLES en zonas de construcción si hay trabajadores presentes"
                },
                "explanation_en": "Workers are fixing the road ahead. Slow down. Watch for workers. Fines are DOUBLED in work zones."
            },
            
            # Add 30+ more construction signs...
        }
    
    # ============================================================================
    # TRANSLATION & EXPLANATION METHODS
    # ============================================================================
    
    def get_sign_info(self, sign_text: str, target_lang: str = 'es') -> Optional[Dict]:
        """
        Get complete information about a road sign
        
        Returns:
        - Translation
        - ELI5 explanation
        - What to do (action steps)
        - Visual description
        - Legal consequences
        - Common mistakes
        """
        sign_upper = sign_text.upper().strip()
        
        # Search all sign databases
        all_signs = {
            **self.regulatory_signs,
            **self.warning_signs,
            **self.guide_signs,
            **self.parking_signs,
            **self.construction_signs
        }
        
        # Try exact match first
        if sign_upper in all_signs:
            sign_data = all_signs[sign_upper]
            
            if target_lang in sign_data:
                lang_data = sign_data[target_lang]
                
                return {
                    'original_sign': sign_text,
                    'category': sign_data['category'],
                    'visual_description': sign_data['visual'],
                    'translation': lang_data['translation'],
                    'eli5_explanation': lang_data['eli5'],
                    'what_to_do': lang_data.get('what_to_do', []),
                    'common_mistake': lang_data.get('common_mistake', ''),
                    'penalty': lang_data.get('penalty', ''),
                    'danger_level': lang_data.get('danger_level', ''),
                    'english_explanation': sign_data.get('explanation_en', '')
                }
        
        # Try partial match
        for sign_key, sign_data in all_signs.items():
            if sign_key in sign_upper or sign_upper in sign_key:
                if target_lang in sign_data:
                    lang_data = sign_data[target_lang]
                    return {
                        'original_sign': sign_text,
                        'matched_sign': sign_key,
                        'category': sign_data['category'],
                        'translation': lang_data['translation'],
                        'eli5_explanation': lang_data['eli5']
                    }
        
        return None


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
road_signs = RoadSignsELI5()

# Test examples
if __name__ == "__main__":
    print("\n" + "="*60)
    print("ROAD SIGNS ELI5 - TRAFFIC SIGN EXPLANATIONS")
    print("="*60)
    
    # Test 1: STOP sign
    print("\n**TEST 1: STOP Sign**")
    stop_info = road_signs.get_sign_info("STOP", "es")
    print(f"Sign: {stop_info['original_sign']}")
    print(f"Translation: {stop_info['translation']}")
    print(f"Explanation: {stop_info['eli5_explanation']}")
    print(f"\nWhat to do:")
    for step in stop_info['what_to_do']:
        print(f"  {step}")
    print(f"\nCommon mistake: {stop_info['common_mistake']}")
    print(f"Penalty: {stop_info['penalty']}")
    
    # Test 2: YIELD sign
    print("\n**TEST 2: YIELD Sign**")
    yield_info = road_signs.get_sign_info("YIELD", "es")
    print(f"Sign: {yield_info['original_sign']}")
    print(f"Translation: {yield_info['translation']}")
    print(f"Explanation: {yield_info['eli5_explanation']}")
    
    # Test 3: School Zone
    print("\n**TEST 3: SCHOOL ZONE Sign**")
    school_info = road_signs.get_sign_info("SCHOOL ZONE", "es")
    print(f"Sign: {school_info['original_sign']}")
    print(f"Translation: {school_info['translation']}")
    print(f"Explanation: {school_info['eli5_explanation']}")
    print(f"Danger: {school_info.get('danger_level', 'N/A')}")
    
    print("\n" + "="*60)
