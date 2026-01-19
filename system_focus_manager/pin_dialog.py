"""
Dialog windows for the PIN system.
Users can enter or configure their PIN here.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QCheckBox, QMessageBox, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from translations import lang


class PINDialog(QDialog):
    """Window to enter PIN"""

    def __init__(self, parent, title="Enter PIN", message="Enter your PIN to continue:"):
        super().__init__(parent)
        self.result = None
        self.setWindowTitle(title)
        self.setMinimumSize(400, 250)
        self.setModal(True)

        self.create_widgets(message)

        # Focus on PIN field
        self.pin_entry.setFocus()

    def create_widgets(self, message):
        """Creates the dialog interface"""

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #3498db; min-height: 60px;")
        header_layout = QVBoxLayout(header_frame)

        header_label = QLabel(lang.get('pin_auth_header'))
        header_label.setFont(QFont('Arial', 14, QFont.Bold))
        header_label.setStyleSheet("color: white;")
        header_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(header_label)

        layout.addWidget(header_frame)

        # Container for the rest
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Message
        msg_label = QLabel(message)
        msg_label.setFont(QFont('Arial', 11))
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(msg_label)

        # PIN field
        self.pin_entry = QLineEdit()
        self.pin_entry.setFont(QFont('Arial', 16))
        self.pin_entry.setEchoMode(QLineEdit.Password)
        self.pin_entry.setAlignment(Qt.AlignCenter)
        self.pin_entry.setMaxLength(20)
        self.pin_entry.returnPressed.connect(self.submit)
        content_layout.addWidget(self.pin_entry)

        # Buttons
        btn_layout = QHBoxLayout()

        ok_btn = QPushButton(lang.get('pin_confirm_btn'))
        ok_btn.setFont(QFont('Arial', 11, QFont.Bold))
        ok_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 35px;")
        ok_btn.clicked.connect(self.submit)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton(lang.get('pin_cancel_btn'))
        cancel_btn.setFont(QFont('Arial', 11))
        cancel_btn.setMinimumHeight(35)
        cancel_btn.clicked.connect(self.cancel)
        btn_layout.addWidget(cancel_btn)

        content_layout.addLayout(btn_layout)

        # Forgot PIN link
        forgot_btn = QPushButton("¿Olvidaste tu PIN?" if lang.get_current_language() == 'es' else "Forgot your PIN?")
        forgot_btn.setFont(QFont('Arial', 9))
        forgot_btn.setStyleSheet("border: none; color: white; text-decoration: underline;")
        forgot_btn.setCursor(Qt.PointingHandCursor)
        forgot_btn.clicked.connect(self.recover_pin)
        content_layout.addWidget(forgot_btn)

        layout.addWidget(content_widget)
        self.setLayout(layout)

    def submit(self):
        """Submits entered PIN"""
        self.result = self.pin_entry.text()
        self.accept()

    def cancel(self):
        """Cancels the dialog"""
        self.result = None
        self.reject()

    def recover_pin(self):
        """Opens PIN recovery dialog"""
        # Import here to avoid circular import
        from pin_manager import PINManager

        pin_manager = PINManager()

        if not pin_manager.has_security_question():
            QMessageBox.warning(
                self,
                "No disponible" if lang.get_current_language() == 'es' else "Not available",
                "No hay pregunta de seguridad configurada. Contacte al administrador." if lang.get_current_language() == 'es' else "No security question configured. Contact the administrator."
            )
            return

        # Open recovery dialog
        recover_dialog = RecoverPINDialog(self, pin_manager)
        if recover_dialog.show():
            # PIN recovered successfully, close this dialog
            QMessageBox.information(
                self,
                "PIN Recuperado" if lang.get_current_language() == 'es' else "PIN Recovered",
                "Ahora puede usar su nuevo PIN" if lang.get_current_language() == 'es' else "You can now use your new PIN"
            )
            self.reject()  # Close the PIN entry dialog

    def show(self):
        """Show dialog and wait for response"""
        self.exec()
        return self.result


class SetPINDialog(QDialog):
    """Window to configure a new PIN"""

    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        self.setWindowTitle(lang.get('pin_setup_title'))
        self.setMinimumSize(450, 400)
        self.setModal(True)

        self.create_widgets()

        # Focus on first field
        self.pin1_entry.setFocus()

    def create_widgets(self):
        """Creates interface to configure PIN"""

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #3498db; min-height: 60px;")
        header_layout = QVBoxLayout(header_frame)

        header_label = QLabel(lang.get('pin_setup_header'))
        header_label.setFont(QFont('Arial', 14, QFont.Bold))
        header_label.setStyleSheet("color: white;")
        header_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(header_label)

        layout.addWidget(header_frame)

        # Container for the rest
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Instructions
        info_label = QLabel(lang.get('pin_setup_instructions'))
        info_label.setFont(QFont('Arial', 10))
        info_label.setStyleSheet("color: #7f8c8d;")
        info_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(info_label)

        # First PIN
        label1 = QLabel(lang.get('pin_enter_your_pin'))
        label1.setFont(QFont('Arial', 11, QFont.Bold))
        content_layout.addWidget(label1)

        self.pin1_entry = QLineEdit()
        self.pin1_entry.setFont(QFont('Arial', 16))
        self.pin1_entry.setEchoMode(QLineEdit.Password)
        self.pin1_entry.setAlignment(Qt.AlignCenter)
        self.pin1_entry.setMaxLength(20)
        content_layout.addWidget(self.pin1_entry)

        # Confirm PIN
        label2 = QLabel(lang.get('pin_confirm_your_pin'))
        label2.setFont(QFont('Arial', 11, QFont.Bold))
        content_layout.addWidget(label2)

        self.pin2_entry = QLineEdit()
        self.pin2_entry.setFont(QFont('Arial', 16))
        self.pin2_entry.setEchoMode(QLineEdit.Password)
        self.pin2_entry.setAlignment(Qt.AlignCenter)
        self.pin2_entry.setMaxLength(20)
        self.pin2_entry.returnPressed.connect(self.submit)
        content_layout.addWidget(self.pin2_entry)

        # Checkbox for parental mode
        self.parental_check = QCheckBox(lang.get('pin_enable_parental'))
        self.parental_check.setFont(QFont('Arial', 10))
        self.parental_check.setChecked(True)
        content_layout.addWidget(self.parental_check)

        # Security questions are now MANDATORY - no checkbox needed
        # Store security question data
        self.security_question_data = None

        # Buttons
        btn_layout = QHBoxLayout()

        ok_btn = QPushButton(lang.get('pin_save_btn'))
        ok_btn.setFont(QFont('Arial', 11, QFont.Bold))
        ok_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 40px;")
        ok_btn.clicked.connect(self.submit)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton(lang.get('cancel'))
        cancel_btn.setFont(QFont('Arial', 11))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.cancel)
        btn_layout.addWidget(cancel_btn)

        content_layout.addLayout(btn_layout)

        layout.addWidget(content_widget)
        self.setLayout(layout)

    def submit(self):
        """Validates and saves PIN"""
        pin1 = self.pin1_entry.text()
        pin2 = self.pin2_entry.text()

        # Validations
        if not pin1 or not pin2:
            QMessageBox.critical(self, "Error", lang.get('pin_error_empty'))
            return

        if len(pin1) < 4:
            QMessageBox.critical(self, "Error", lang.get('pin_error_short'))
            return

        if pin1 != pin2:
            QMessageBox.critical(self, "Error", lang.get('pin_error_mismatch'))
            self.pin1_entry.clear()
            self.pin2_entry.clear()
            self.pin1_entry.setFocus()
            return

        # Security questions are now MANDATORY
        security_dialog = SecurityQuestionDialog(self)
        self.security_question_data = security_dialog.show()

        if not self.security_question_data:
            QMessageBox.warning(
                self,
                "Requerido" if lang.get_current_language() == 'es' else "Required",
                "Debe configurar las preguntas de seguridad para continuar" if lang.get_current_language() == 'es' else "You must configure security questions to continue"
            )
            return

        # Valid PIN
        self.result = {
            'pin': pin1,
            'parental_mode': self.parental_check.isChecked(),
            'security_question': self.security_question_data
        }
        self.accept()

    def cancel(self):
        """Cancels configuration"""
        self.result = None
        self.reject()

    def show(self):
        """Show dialog and wait for response"""
        self.exec()
        return self.result


class SecurityQuestionDialog(QDialog):
    """Window to configure security questions for PIN recovery - Select 3-5 questions"""

    # Predefined security questions
    SECURITY_QUESTIONS_ES = [
        "¿Cuál es el nombre de tu primera mascota?",
        "¿En qué ciudad naciste?",
        "¿Cuál es el nombre de tu mejor amigo de la infancia?",
        "¿Cuál es tu comida favorita?",
        "¿Cuál es el nombre de tu escuela primaria?"
    ]

    SECURITY_QUESTIONS_EN = [
        "What is the name of your first pet?",
        "What city were you born in?",
        "What is the name of your childhood best friend?",
        "What is your favorite food?",
        "What is the name of your elementary school?"
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        self.setWindowTitle("Configurar Preguntas de Seguridad" if lang.get_current_language() == 'es' else "Configure Security Questions")
        self.setMinimumSize(600, 650)
        self.setModal(True)

        # Store checkboxes and answer fields
        self.question_checkboxes = []
        self.answer_fields = []

        self.create_widgets()

    def create_widgets(self):
        """Creates interface to select and answer 3-5 security questions"""
        from PySide6.QtWidgets import QScrollArea, QGroupBox

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #3498db; min-height: 60px;")
        header_layout = QVBoxLayout(header_frame)

        header_label = QLabel("PREGUNTAS DE SEGURIDAD" if lang.get_current_language() == 'es' else "SECURITY QUESTIONS")
        header_label.setFont(QFont('Arial', 14, QFont.Bold))
        header_label.setStyleSheet("color: white;")
        header_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(header_label)

        layout.addWidget(header_frame)

        # Scroll area for questions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Instructions
        info_label = QLabel(
            "Selecciona entre 2 y 5 preguntas de seguridad y responde cada una.\n"
            "Estas preguntas te ayudarán a recuperar tu PIN si lo olvidas."
            if lang.get_current_language() == 'es' else
            "Select between 2 and 5 security questions and answer each one.\n"
            "These questions will help you recover your PIN if you forget it."
        )
        info_label.setFont(QFont('Arial', 10))
        info_label.setStyleSheet("color: #7f8c8d; padding: 10px;")
        info_label.setWordWrap(True)
        content_layout.addWidget(info_label)

        # Get questions based on language
        questions = self.SECURITY_QUESTIONS_ES if lang.get_current_language() == 'es' else self.SECURITY_QUESTIONS_EN

        # Create a group for each question
        for i, question in enumerate(questions):
            group = QGroupBox()
            group.setStyleSheet("""
                QGroupBox {
                    border: 2px solid #e0e0e0;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
            """)
            group_layout = QVBoxLayout()

            # Checkbox with question
            checkbox = QCheckBox(question)
            checkbox.setFont(QFont('Arial', 10, QFont.Bold))
            checkbox.setStyleSheet("color: #2c3e50;")
            checkbox.toggled.connect(lambda checked, idx=i: self.on_question_toggled(idx, checked))
            group_layout.addWidget(checkbox)
            self.question_checkboxes.append(checkbox)

            # Answer field
            answer_label = QLabel("Respuesta:" if lang.get_current_language() == 'es' else "Answer:")
            answer_label.setFont(QFont('Arial', 9))
            answer_label.setStyleSheet("color: #7f8c8d; margin-left: 20px;")
            group_layout.addWidget(answer_label)

            answer_field = QLineEdit()
            answer_field.setFont(QFont('Arial', 10))
            answer_field.setEchoMode(QLineEdit.Password)
            answer_field.setEnabled(False)
            answer_field.setStyleSheet("margin-left: 20px; margin-right: 10px;")
            group_layout.addWidget(answer_field)
            self.answer_fields.append(answer_field)

            group.setLayout(group_layout)
            content_layout.addWidget(group)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # Buttons
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)

        ok_btn = QPushButton("GUARDAR" if lang.get_current_language() == 'es' else "SAVE")
        ok_btn.setFont(QFont('Arial', 11, QFont.Bold))
        ok_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 40px;")
        ok_btn.clicked.connect(self.submit)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("CANCELAR" if lang.get_current_language() == 'es' else "CANCEL")
        cancel_btn.setFont(QFont('Arial', 11))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.cancel)
        btn_layout.addWidget(cancel_btn)

        layout.addWidget(btn_widget)
        self.setLayout(layout)

    def on_question_toggled(self, index, checked):
        """Enable/disable answer fields when checkbox is toggled"""
        self.answer_fields[index].setEnabled(checked)
        if not checked:
            self.answer_fields[index].clear()

    def submit(self):
        """Validates and saves selected security questions (2-5 required)"""
        # Get questions based on language
        questions = self.SECURITY_QUESTIONS_ES if lang.get_current_language() == 'es' else self.SECURITY_QUESTIONS_EN

        # Collect selected questions and answers
        selected_qa = []
        for i, checkbox in enumerate(self.question_checkboxes):
            if checkbox.isChecked():
                answer = self.answer_fields[i].text().strip()

                # Validate each selected question
                if not answer:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Debe responder la pregunta:\n{questions[i]}" if lang.get_current_language() == 'es'
                        else f"You must answer the question:\n{questions[i]}"
                    )
                    return

                if len(answer) < 3:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"La respuesta debe tener al menos 3 caracteres:\n{questions[i]}" if lang.get_current_language() == 'es'
                        else f"Answer must be at least 3 characters:\n{questions[i]}"
                    )
                    return

                selected_qa.append({
                    'question': questions[i],
                    'answer': answer.lower().strip()
                })

        # Validate 2-5 questions selected
        if len(selected_qa) < 2:
            QMessageBox.critical(
                self,
                "Error",
                f"Debe seleccionar al menos 2 preguntas (seleccionó {len(selected_qa)})" if lang.get_current_language() == 'es'
                else f"You must select at least 2 questions (selected {len(selected_qa)})"
            )
            return

        if len(selected_qa) > 5:
            QMessageBox.critical(
                self,
                "Error",
                f"Debe seleccionar máximo 5 preguntas (seleccionó {len(selected_qa)})" if lang.get_current_language() == 'es'
                else f"You must select maximum 5 questions (selected {len(selected_qa)})"
            )
            return

        # Valid - return list of Q&A
        self.result = {
            'questions': selected_qa
        }
        self.accept()

    def cancel(self):
        """Cancels configuration"""
        self.result = None
        self.reject()

    def show(self):
        """Show dialog and wait for response"""
        self.exec()
        return self.result


class RecoverPINDialog(QDialog):
    """Window to recover forgotten PIN by answering ONE of the 3 security questions"""

    def __init__(self, parent, pin_manager):
        super().__init__(parent)
        self.pin_manager = pin_manager
        self.result = None
        self.setWindowTitle("Recuperar PIN" if lang.get_current_language() == 'es' else "Recover PIN")
        self.setMinimumSize(600, 650)
        self.setModal(True)

        # Check if security questions exist
        if not self.pin_manager.has_security_question():
            QMessageBox.critical(
                parent,
                "Error",
                "No hay preguntas de seguridad configuradas. No se puede recuperar el PIN." if lang.get_current_language() == 'es' else "No security questions configured. Cannot recover PIN."
            )
            self.reject()
            return

        # Get all security questions
        self.security_questions = self.pin_manager.get_security_questions()
        self.answer_fields = []

        self.create_widgets()

    def create_widgets(self):
        """Creates interface to recover PIN by answering ONE security question"""
        from PySide6.QtWidgets import QScrollArea, QGroupBox

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #3498db; min-height: 60px;")
        header_layout = QVBoxLayout(header_frame)

        header_label = QLabel("RECUPERAR PIN" if lang.get_current_language() == 'es' else "RECOVER PIN")
        header_label.setFont(QFont('Arial', 14, QFont.Bold))
        header_label.setStyleSheet("color: white;")
        header_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(header_label)

        layout.addWidget(header_frame)

        # Scroll area for questions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Instructions
        info_label = QLabel(
            f"Responde correctamente UNA de las {len(self.security_questions)} preguntas de seguridad para recuperar tu PIN"
            if lang.get_current_language() == 'es' else
            f"Answer ONE of the {len(self.security_questions)} security questions correctly to recover your PIN"
        )
        info_label.setFont(QFont('Arial', 10))
        info_label.setStyleSheet("color: #7f8c8d; padding: 10px;")
        info_label.setWordWrap(True)
        content_layout.addWidget(info_label)

        # Display all security questions
        for i, qa in enumerate(self.security_questions):
            question = qa['question']

            group = QGroupBox()
            group.setStyleSheet("""
                QGroupBox {
                    border: 2px solid #3498db;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
            """)
            group_layout = QVBoxLayout()

            # Question label
            q_label = QLabel(f"{i+1}. {question}")
            q_label.setFont(QFont('Arial', 11, QFont.Bold))
            q_label.setStyleSheet("color: #2c3e50;")
            q_label.setWordWrap(True)
            group_layout.addWidget(q_label)

            # Answer field
            answer_label = QLabel("Respuesta:" if lang.get_current_language() == 'es' else "Answer:")
            answer_label.setFont(QFont('Arial', 9))
            answer_label.setStyleSheet("color: #7f8c8d; margin-left: 10px;")
            group_layout.addWidget(answer_label)

            answer_field = QLineEdit()
            answer_field.setFont(QFont('Arial', 11))
            answer_field.setStyleSheet("margin-left: 10px; margin-right: 10px;")
            answer_field.setPlaceholderText("Ingresa tu respuesta..." if lang.get_current_language() == 'es' else "Enter your answer...")
            group_layout.addWidget(answer_field)
            self.answer_fields.append(answer_field)

            group.setLayout(group_layout)
            content_layout.addWidget(group)

        # New PIN section
        new_pin_label = QLabel("Nuevo PIN:" if lang.get_current_language() == 'es' else "New PIN:")
        new_pin_label.setFont(QFont('Arial', 11, QFont.Bold))
        content_layout.addWidget(new_pin_label)

        self.new_pin_entry = QLineEdit()
        self.new_pin_entry.setFont(QFont('Arial', 16))
        self.new_pin_entry.setEchoMode(QLineEdit.Password)
        self.new_pin_entry.setAlignment(Qt.AlignCenter)
        self.new_pin_entry.setMaxLength(20)
        content_layout.addWidget(self.new_pin_entry)

        # Confirm new PIN
        confirm_pin_label = QLabel("Confirmar nuevo PIN:" if lang.get_current_language() == 'es' else "Confirm new PIN:")
        confirm_pin_label.setFont(QFont('Arial', 11, QFont.Bold))
        content_layout.addWidget(confirm_pin_label)

        self.confirm_pin_entry = QLineEdit()
        self.confirm_pin_entry.setFont(QFont('Arial', 16))
        self.confirm_pin_entry.setEchoMode(QLineEdit.Password)
        self.confirm_pin_entry.setAlignment(Qt.AlignCenter)
        self.confirm_pin_entry.setMaxLength(20)
        self.confirm_pin_entry.returnPressed.connect(self.submit)
        content_layout.addWidget(self.confirm_pin_entry)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # Buttons (outside scroll area)
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)

        ok_btn = QPushButton("RECUPERAR PIN" if lang.get_current_language() == 'es' else "RECOVER PIN")
        ok_btn.setFont(QFont('Arial', 11, QFont.Bold))
        ok_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 40px;")
        ok_btn.clicked.connect(self.submit)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("CANCELAR" if lang.get_current_language() == 'es' else "CANCEL")
        cancel_btn.setFont(QFont('Arial', 11))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.cancel)
        btn_layout.addWidget(cancel_btn)

        layout.addWidget(btn_widget)
        self.setLayout(layout)

    def submit(self):
        """Validates that at least ONE answer is correct and resets PIN"""
        # Collect all answers (allow empty answers)
        answers = {}
        has_any_answer = False

        for i, qa in enumerate(self.security_questions):
            question = qa['question']
            answer = self.answer_fields[i].text().strip()
            answers[question] = answer
            if answer:
                has_any_answer = True

        # Check if at least one answer was provided
        if not has_any_answer:
            QMessageBox.critical(
                self,
                "Error",
                "Debe responder al menos una pregunta de seguridad" if lang.get_current_language() == 'es'
                else "You must answer at least one security question"
            )
            return

        # Validate new PIN
        new_pin = self.new_pin_entry.text()
        confirm_pin = self.confirm_pin_entry.text()

        if not new_pin or not confirm_pin:
            QMessageBox.critical(self, "Error", "Debe ingresar el nuevo PIN" if lang.get_current_language() == 'es' else "You must enter the new PIN")
            return

        if len(new_pin) < 4:
            QMessageBox.critical(self, "Error", "El PIN debe tener al menos 4 caracteres" if lang.get_current_language() == 'es' else "PIN must be at least 4 characters")
            return

        if new_pin != confirm_pin:
            QMessageBox.critical(self, "Error", "Los PINs no coinciden" if lang.get_current_language() == 'es' else "PINs do not match")
            self.new_pin_entry.clear()
            self.confirm_pin_entry.clear()
            self.new_pin_entry.setFocus()
            return

        # Verify at least ONE security answer is correct
        if not self.pin_manager.verify_any_security_answer(answers):
            QMessageBox.critical(
                self,
                "Error",
                "Ninguna de las respuestas es correcta. Debe responder correctamente al menos una pregunta." if lang.get_current_language() == 'es'
                else "None of the answers are correct. You must answer at least one question correctly."
            )
            # Clear all answer fields
            for field in self.answer_fields:
                field.clear()
            self.answer_fields[0].setFocus()
            return

        # Reset PIN
        if self.pin_manager.reset_pin_with_any_security_answer(new_pin, answers):
            QMessageBox.information(
                self,
                "Éxito" if lang.get_current_language() == 'es' else "Success",
                "PIN recuperado exitosamente" if lang.get_current_language() == 'es' else "PIN recovered successfully"
            )
            self.result = True
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Error al recuperar PIN" if lang.get_current_language() == 'es' else "Error recovering PIN")

    def cancel(self):
        """Cancels recovery"""
        self.result = None
        self.reject()

    def show(self):
        """Show dialog and wait for response"""
        self.exec()
        return self.result
