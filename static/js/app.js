function addMessage(text, sender) {
    const chat = document.getElementById("chat");
    const div = document.createElement("div");
    div.className = sender; 
    
    const textSpan = document.createElement("span");
    textSpan.innerHTML = text.replace(/\n/g, '<br>'); 
    div.appendChild(textSpan);

    if (sender === "bot") {
        const speakBtn = document.createElement("button");
        speakBtn.innerText = "🔊"; 
        speakBtn.title = "กดเพื่อฟังเสียง";
        speakBtn.style.cssText = "background: none; border: none; cursor: pointer; margin-left: 10px; font-size: 1.2rem; outline: none;";
        
        speakBtn.onclick = () => botSpeak(text);
        
        div.appendChild(speakBtn);
    }

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight; 
}

function ask() {
    const input = document.getElementById("q");
    const q = input.value.trim();
    
    if (!q) return; 

    addMessage(q, "user"); 
    input.value = ""; 

    fetch(`/ask?q=${encodeURIComponent(q)}`)
        .then(r => r.json())
        .then(data => {
            setTimeout(() => {
                const answerText = data.answer || "ขออภัยค่ะ ไม่พบข้อมูล";
                addMessage(answerText, "bot"); 
                botSpeak(answerText); 
            }, 300); 
        })
        .catch(err => {
            console.error("Error:", err);
            addMessage("⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อ", "bot");
        });
}

document.getElementById("q").addEventListener("keypress", (e) => {
    if (e.key === "Enter") ask();
});

const micBtn = document.getElementById("mic-btn");
const inputField = document.getElementById("q");
const micIcon = micBtn ? micBtn.querySelector("i") : null;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition && micBtn) {
    const recognition = new SpeechRecognition();
    recognition.lang = "th-TH"; 
    recognition.continuous = false; 

    micBtn.addEventListener("click", () => {
        recognition.start();
    });

    recognition.onstart = () => {
        if(micIcon) {
            micIcon.className = "fa-solid fa-circle-dot";
            micIcon.style.color = "red";
        } else {
            micBtn.innerText = "🔴";
        }
        inputField.placeholder = "กำลังฟัง... (พูดได้เลย)";
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        inputField.value = transcript; 
    };

    recognition.onend = () => {
        if(micIcon) {
            micIcon.className = "fa-solid fa-microphone";
            micIcon.style.color = "";
        } else {
            micBtn.innerText = "🎤";
        }
        inputField.placeholder = "พิมพ์ข้อความที่นี่...";
    };

    recognition.onerror = (event) => {
        console.error("Speech Error:", event.error);
        if(micIcon) {
            micIcon.className = "fa-solid fa-microphone";
            micIcon.style.color = "";
        } else {
            micBtn.innerText = "🎤";
        }
        inputField.placeholder = "ไม่ได้ยินเสียง รบกวนกดใหม่ค่ะ";
    };

} else {
    if(micBtn) micBtn.style.display = "none";
}

function botSpeak(text) {
    if ('speechSynthesis' in window) {
        let cleanText = text.replace(/\*\*/g, "") 
                            .replace(/[🏥📞📍⏳❌🚨]/g, ""); 

        let utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = "th-TH"; 
        utterance.rate = 1.0;    
        utterance.pitch = 1.0;   

        window.speechSynthesis.speak(utterance);
    } else {
        console.warn("เบราว์เซอร์ของคุณไม่รองรับระบบอ่านออกเสียงค่ะ");
    }
}
