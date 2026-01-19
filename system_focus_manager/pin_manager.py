"""
Here I handle the entire PIN system for parental mode.
I encrypt the PIN with SHA-256 to make it secure.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Optional


class PINManager:
    """My PIN manager for parental control"""

    def __init__(self):
        # Use LOCALAPPDATA for persistent storage
        app_data = os.path.expandvars('%LOCALAPPDATA%')
        self.config_file = Path(app_data) / 'FocusManager' / 'config' / 'pin_config.json'
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()

    def load_config(self) -> dict:
        """Load PIN configuration if it exists"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass

        # Default configuration
        return {
            'pin_enabled': False,
            'pin_hash': None,
            'parental_mode': False,
            'require_pin_to_exit': False,
            'security_question': None,
            'security_answer_hash': None
        }

    def save_config(self):
        """Save PIN configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error guardando config: {e}")
            return False

    def hash_pin(self, pin: str) -> str:
        """Encrypt PIN with SHA-256 for security"""
        return hashlib.sha256(pin.encode()).hexdigest()

    def set_pin(self, pin: str, security_questions: list = None) -> bool:
        """
        Set up a new PIN with optional security questions.
        security_questions should be a list of dicts: [{'question': str, 'answer': str}, ...]
        """
        if not pin or len(pin) < 4:
            return False

        self.config['pin_hash'] = self.hash_pin(pin)
        self.config['pin_enabled'] = True

        # Save security questions if provided (3-5 questions)
        if security_questions and isinstance(security_questions, list):
            hashed_questions = []
            for qa in security_questions:
                hashed_questions.append({
                    'question': qa['question'],
                    'answer_hash': self.hash_pin(qa['answer'].lower().strip())
                })
            self.config['security_questions'] = hashed_questions

            # Keep old format for compatibility
            if hashed_questions:
                self.config['security_question'] = hashed_questions[0]['question']
                self.config['security_answer_hash'] = hashed_questions[0]['answer_hash']

        return self.save_config()

    def verify_pin(self, pin: str) -> bool:
        """Verify if the entered PIN is correct"""
        if not self.config['pin_enabled']:
            return True  # If there's no PIN, always valid

        if not self.config['pin_hash']:
            return True

        return self.hash_pin(pin) == self.config['pin_hash']

    def remove_pin(self):
        """Remove PIN (disable protection)"""
        self.config['pin_hash'] = None
        self.config['pin_enabled'] = False
        self.config['parental_mode'] = False
        self.config['require_pin_to_exit'] = False
        return self.save_config()

    def enable_parental_mode(self, enabled: bool = True):
        """Enable/disable parental mode"""
        self.config['parental_mode'] = enabled
        return self.save_config()

    def set_require_pin_to_exit(self, required: bool = True):
        """Configure if PIN is required to exit"""
        self.config['require_pin_to_exit'] = required
        return self.save_config()

    def is_pin_enabled(self) -> bool:
        """Check if there's a PIN configured"""
        return self.config.get('pin_enabled', False)

    def is_parental_mode(self) -> bool:
        """Check if parental mode is active"""
        return self.config.get('parental_mode', False)

    def has_security_question(self) -> bool:
        """Check if security questions are configured"""
        return bool(self.config.get('security_questions') or
                   (self.config.get('security_question') and self.config.get('security_answer_hash')))

    def get_security_questions(self) -> list:
        """Get all security questions"""
        questions = self.config.get('security_questions', [])
        if questions:
            return [{'question': q['question']} for q in questions]

        # Fallback to old format
        old_question = self.config.get('security_question')
        if old_question:
            return [{'question': old_question}]

        return []

    def get_security_question(self) -> Optional[str]:
        """Get the first security question (for compatibility)"""
        questions = self.get_security_questions()
        return questions[0]['question'] if questions else None

    def verify_security_answers(self, answers: dict) -> bool:
        """
        Verify if ALL security answers are correct.
        answers should be a dict: {'question': 'answer', ...}
        """
        questions = self.config.get('security_questions', [])
        if not questions:
            # Fallback to old format
            return self.verify_security_answer(list(answers.values())[0])

        # All questions must be answered correctly
        for qa in questions:
            question = qa['question']
            if question not in answers:
                return False

            answer_hash = self.hash_pin(answers[question].lower().strip())
            if answer_hash != qa['answer_hash']:
                return False

        return True

    def verify_any_security_answer(self, answers: dict) -> bool:
        """
        Verify if AT LEAST ONE security answer is correct.
        answers should be a dict: {'question': 'answer', ...}
        Returns True if any answer matches its question.
        """
        questions = self.config.get('security_questions', [])
        if not questions:
            # Fallback to old format
            return self.verify_security_answer(list(answers.values())[0])

        # Check if at least one answer is correct
        for qa in questions:
            question = qa['question']
            if question in answers:
                answer = answers[question]
                if answer and answer.strip():  # Only check non-empty answers
                    answer_hash = self.hash_pin(answer.lower().strip())
                    if answer_hash == qa['answer_hash']:
                        return True  # Found a correct answer

        return False  # No correct answers found

    def verify_security_answer(self, answer: str) -> bool:
        """Verify if the security answer is correct (single question - old format)"""
        if not self.has_security_question():
            return False

        answer_hash = self.hash_pin(answer.lower().strip())

        # Try new format first
        questions = self.config.get('security_questions', [])
        if questions:
            return answer_hash == questions[0]['answer_hash']

        # Fallback to old format
        return answer_hash == self.config.get('security_answer_hash')

    def reset_pin_with_security_answers(self, new_pin: str, answers: dict) -> bool:
        """Reset PIN using all security answers"""
        if not self.verify_security_answers(answers):
            return False

        self.config['pin_hash'] = self.hash_pin(new_pin)
        return self.save_config()

    def reset_pin_with_any_security_answer(self, new_pin: str, answers: dict) -> bool:
        """Reset PIN using at least one correct security answer"""
        if not self.verify_any_security_answer(answers):
            return False

        self.config['pin_hash'] = self.hash_pin(new_pin)
        return self.save_config()

    def reset_pin_with_security_answer(self, new_pin: str, security_answer: str) -> bool:
        """Reset PIN using security answer (single - old format)"""
        if not self.verify_security_answer(security_answer):
            return False

        self.config['pin_hash'] = self.hash_pin(new_pin)
        return self.save_config()

    def requires_pin_to_exit(self) -> bool:
        """Check if PIN is required to exit"""
        return self.config.get('require_pin_to_exit', False)

    def has_pin(self) -> bool:
        """Check if a PIN exists configured"""
        return self.config.get('pin_hash') is not None
