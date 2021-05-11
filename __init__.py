# fallback-aiml
# Copyright (C) 2017  Mycroft AI
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import aiml
import os
from os import listdir, remove as remove_file
from os.path import dirname, isfile

from mycroft.api import DeviceApi
from mycroft.skills.core import MycroftSkill
from mycroft.skills.core import intent_handler, intent_file_handler
from adapt.intent import IntentBuilder


class Chatbot(MycroftSkill):

    chatting = False

    def __init__(self):
        super(Chatbot, self).__init__(name='Winston_Chatbot')
        self.kernel = aiml.Kernel()
#        chatbot_brain = self.settings.get('chatbot_brain')
        chatbot_brain = "AnnaL"
        self.aiml_path = os.path.join(dirname(__file__), chatbot_brain)
        self.brain_path = os.path.join(self.file_system.path, 'bot_brain.brn')
        # reloading skills will also reset this 'timer', so ideally it should
        # not be too high
        self.line_count = 1
        self.save_loop_threshold = int(self.settings.get('save_loop_threshold',
                                                         4))

        self.brain_loaded = False

    def load_brain(self):
        """Set up the aiml engine using available device information."""
        self.log.info('Loading Brain')
        if isfile(self.brain_path):
            self.kernel.bootstrap(brainFile=self.brain_path)
        else:
            aimls = listdir(self.aiml_path)
            for aiml_file in aimls:
                self.kernel.learn(os.path.join(self.aiml_path, aiml_file))
            self.kernel.saveBrain(self.brain_path)
        try:
            device = DeviceApi().get()
        except Exception:
            device = {
                "name": "Mycroft",
                "platform": "AI"
            }
        self.kernel.setBotPredicate("name", device["name"])
        self.kernel.setBotPredicate("species", device["platform"])
        self.kernel.setBotPredicate("genus", "Mycroft")
        self.kernel.setBotPredicate("family", "virtual personal assistant")
        self.kernel.setBotPredicate("order", "artificial intelligence")
        self.kernel.setBotPredicate("class", "computer program")
        self.kernel.setBotPredicate("kingdom", "machine")
        self.kernel.setBotPredicate("hometown", "127.0.0.1")
        self.kernel.setBotPredicate("botmaster", "master")
        self.kernel.setBotPredicate("master", "the community")
        # IDEA: extract age from
        # https://api.github.com/repos/MycroftAI/mycroft-core created_at date
        self.kernel.setBotPredicate("age", "20")

        self.brain_loaded = True
        return

    @intent_handler(IntentBuilder("ResetMemoryIntent").require("Reset")
                                                      .require("Memory"))
    def handle_reset_brain(self, message):
        """Delete the stored memory, effectively resetting the brain state."""
        self.log.debug('Deleting brain file')
        # delete the brain file and reset memory
        self.speak_dialog("reset.memory")
        remove_file(self.brain_path)
        self.soft_reset_brain()
        return

    def soft_reset_brain(self):
        # Only reset the active kernel memory
        self.kernel.resetBrain()
        self.brain_loaded = False
        return

    def shutdown(self):
        """Shut down any loaded brain."""
        if self.brain_loaded:
            self.kernel.saveBrain(self.brain_path)
            self.kernel.resetBrain()  # Manual remove
        self.remove_fallback(self.handle_fallback)
        super(Chatbot, self).shutdown()

    @intent_file_handler("start_parrot.intent")
    def handle_start_parrot_intent(self, message):
        self.chatting = True
        self.speak_dialog("chat_start", expect_response=True)

    @intent_file_handler("stop_parrot.intent")
    def handle_stop_parrot_intent(self, message):
        if self.chatting:
            self.chatting = False
            self.speak_dialog("chat_stop")
        else:
            self.speak_dialog("not_chatting")

    def stop(self):
        if self.chatting:
            self.chatting = False
            self.speak_dialog("chat_stop")
            return True
        return False

    def ask_brain(self, utterance):
        """Send a query to the AIML brain.

        Saves the state to disk once in a while.
        """
        response = self.kernel.respond(utterance)
        # make a security copy once in a while
        if (self.line_count % self.save_loop_threshold) == 0:
            self.kernel.saveBrain(self.brain_path)
        self.line_count += 1

        return response

    def converse(self, utterances, lang="en-us"):
        if self.chatting:
            if self.voc_match(utterances[0], "StopKeyword") and self.voc_match(utterances[0], "ChatKeyword"):
                 return False

            if not self.brain_loaded:
                self.load_brain()
            utterance = utterances
            answer = self.ask_brain(utterance)
            if answer != "":
                asked_question = False
                if answer.endswith("?"):
                    asked_question = True
                self.speak(answer, expect_response=asked_question)
                return True
            return True
        else:
            return False


def create_skill():
    return Chatbot()
