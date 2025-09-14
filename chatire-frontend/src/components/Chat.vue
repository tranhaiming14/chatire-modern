<template>
  <div class="container-fluid">

    <!-- Top-right control buttons -->
    <div style="position: absolute; top: 10px; right: 10px; z-index: 1000;">
      <button @click="showAddFriendModal = true" class="btn btn-secondary btn-sm mb-2">
        Add Friend
      </button>
      <br>
      <button @click="showMailbox" class="btn btn-warning btn-sm">
        Mailbox ({{ friendRequests.length }})
      </button>
    </div>

    <div class="row">
      <!-- Chat History Sidebar -->
      <div class="col-sm-3 border-right" style="height: 100vh; overflow-y: auto;">
        <h5 class="p-2">Chat History</h5>
        <ul class="list-group">
          <li v-for="session in chatHistory" 
              :key="session.uri"
              class="list-group-item list-group-item-action"
              @click="goToSession(session.uri)">
            {{ session.name || session.uri }}
          </li>
        </ul>
      </div>

      <!-- Chat Window -->
      <div class="col-sm-6 offset-0">

        <div v-if="sessionStarted" id="chat-container" class="card">
          <div class="card-header text-white text-center font-weight-bold subtle-blue-gradient">
            Share the page URL to invite new friends
          </div>

          <div class="card-body">
            <div class="container chat-body" ref="chatBody">
              <div v-for="message in messages" :key="message.id" class="row chat-section">
                <template v-if="username === message.user.username">
                  <div class="col-sm-7 offset-3">
                    <span class="card-text speech-bubble speech-bubble-user float-right text-white subtle-blue-gradient">
                      {{ message.message }}
                    </span>
                  </div>
                  <div class="col-sm-2">
                    <img class="rounded-circle" :src="generateAvatar(message.user.username)" />
                  </div>
                </template>
                <template v-else>
                  <div class="col-sm-2">
                    <img class="rounded-circle" :src="generateAvatar(message.user.username)" />
                  </div>
                  <div class="col-sm-7">
                    <span class="card-text speech-bubble speech-bubble-peer">
                      {{ message.message }}
                    </span>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <div class="card-footer text-muted">
            <form @submit.prevent="postMessage">
              <div class="row">
                <div class="col-sm-10">
                  <input v-model="message" type="text" placeholder="Type a message" />
                </div>
                <div class="col-sm-2">
                  <button class="btn btn-primary">Send</button>
                </div>
              </div>
            </form>
          </div>
        </div>

        <div v-else>
          <h3 class="text-center">Welcome!</h3>
          <br>
          <p class="text-center">
            To start chatting with friends click on the button below, it'll start a new chat session
            and then you can invite your friends over to chat!
          </p>
          <br>
          <button @click="startChatSession" 
                  class="btn btn-primary btn-lg btn-block">
            Start Chatting
          </button>
        </div>

      </div>
    </div>

    <!-- Add Friend Modal -->
    <div v-if="showAddFriendModal" class="modal-backdrop-custom" @click.self="showAddFriendModal = false">
      <div class="modal-custom">
        <h5>Add Friend</h5>
        <input 
          v-model="friendUsername" 
          class="form-control" 
          placeholder="Enter username"
          @keyup.enter="sendFriendRequest"
        >
        <div class="text-center">
          <button class="btn btn-primary" @click="sendFriendRequest">Send Request</button>
          <button class="btn btn-secondary" @click="showAddFriendModal = false">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Friend Requests Modal -->
    <div v-if="showRequests" class="modal-backdrop-custom" @click.self="showRequests = false">
      <div class="modal-custom">
        <h5>Friend Requests</h5>
        <div v-if="friendRequests.length === 0" class="text-center text-muted">
          <p>No friend requests at the moment</p>
        </div>
        <div v-else>
          <ul class="list-group">
            <li v-for="req in friendRequests" :key="req.id" class="list-group-item d-flex justify-content-between align-items-center">
              <strong>{{ req.from_user }}</strong>
              <div>
                <button class="btn btn-success btn-sm" @click="respondRequest(req.id, 'accept')">Accept</button>
                <button class="btn btn-danger btn-sm" @click="respondRequest(req.id, 'decline')">Decline</button>
              </div>
            </li>
          </ul>
        </div>
        <div class="text-center">
          <button class="btn btn-secondary" @click="showRequests = false">Close</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
export default {
  data () {
    return {
      sessionStarted: false,
      messages: [],
      message: '',
      chatHistory: [],
      currentUri: null, // <-- store URI here
      showAddFriendModal:false,
      showRequests:false,
      friendUsername:'',
      friendRequests:[],
      websocket: null
    }
  },

  created () {
    console.log("Chat.vue created  ", this.$route.fullPath)

    this.username = sessionStorage.getItem('username')

    // Setup headers for all requests
    $.ajaxSetup({
      beforeSend: function(xhr) {
        xhr.setRequestHeader('Authorization', `Token ${sessionStorage.getItem('authToken')}`)
      }
    })
    this.loadChatHistory()

    if (this.$route.params.uri) {
      this.joinChatSession()
    }
    if (this.$route.params.uri) {
      console.log(`Connected to chat session: ${this.$route.params.uri}`)
    }
    this.loadFriendRequests()
  },

  mounted () {
    console.log("Chat.vue mounted", this.$route.fullPath)
    this.loadChatHistory()
  },

    updated () {
  // Scroll to bottom of Chat window
  const chatBody = this.$refs.chatBody
  if (chatBody) {
    chatBody.scrollTop = chatBody.scrollHeight
    }

    },

  methods: {
    startChatSession () {
      $.post({
        url: 'http://localhost:8000/api/chats/',
        contentType: 'application/json',
        dataType: 'json',
        success: (data) => {
          this.$router.push(`/chats/${data.uri}/`).then(() => {
            this.currentUri = data.uri; // save URI immediately
            this.sessionStarted = true
            this.loadChatHistory()
            this.connectToWebSocket() // only now connect

          })
        }
      })
    },

    postMessage (event) {
      const data = {message: this.message}
      const uri = this.currentUri || this.$route.params.uri; // prefer stored URI
      if (!uri) {
        alert("No active chat session!");
        return;
      }

      $.post(`http://localhost:8000/api/chats/${this.$route.params.uri}/messages/`, data, (data) => {
        this.message = '' // clear the message after sending
      })
      .fail((response) => {
        alert(response.responseText)
      })
    },

    joinChatSession () {
      const uri = this.currentUri || this.$route.params.uri; // prefer stored URI
      if (!uri) {
        console.error("❌ No URI for joining chat session")
        return
      }
      this.$.ajax({
        url: `http://localhost:8000/api/chats/${uri}/`,
        data: { username: this.username },
        type: 'PATCH',
        success: (data) => {
          const user = data.members.find((member) => member.username === this.username)

          if (user) {
            // The user belongs/has joined the session
            this.sessionStarted = true
            this.fetchChatSessionHistory()
            this.loadChatHistory()
            this.connectToWebSocket() // ✅ ADD THIS LINE
          }
        }
      })
    },

    fetchChatSessionHistory () {
      this.$.get(`http://127.0.0.1:8000/api/chats/${this.$route.params.uri}/messages/`, (data) => {
        this.messages = data.messages
      })
    },
    connectToWebSocket () {
      const uri = this.currentUri || this.$route.params.uri;
      if (!uri) {
        console.error("❌ No URI for WebSocket connection");
        return;
      }

      // Close existing connection if any
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        console.log("🔌 Closing previous WebSocket connection...");
        this.websocket.close();
      }

      // Create new connection
      this.websocket = new WebSocket(`ws://localhost:8001/ws/chat/${uri}`);
      this.websocket.onopen = this.onOpen;
      this.websocket.onclose = this.onClose;
      this.websocket.onmessage = this.onMessage;
      this.websocket.onerror = this.onError;
    },


    onOpen (event) {
      console.log('Connection opened.', event.data)
    },

    onClose (event) {
      console.log('Connection closed.', event.data)

      // Try and Reconnect after five seconds
      //setTimeout(this.connectToWebSocket, 5000)
    },

    onMessage (event) {
    const data = JSON.parse(event.data);
    console.log("📩 Incoming WebSocket:", event.data); // <-- debug
    this.messages.push({
        user: data.user,
        message: data.message
    });
    },

    onError (event) {
      alert('An error occured:', event.data)
    },
    generateAvatar(username) {
    const canvas = document.createElement('canvas');
    const size = 40;
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');

    // Pick background color from a palette
    const colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1'];
    const color = colors[username.charCodeAt(0) % colors.length];

    // Draw circular background
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();

    // Draw initial letter
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 20px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(username[0].toUpperCase(), size / 2, size / 2);

    // Return image as base64
    return canvas.toDataURL();
  },
    loadChatHistory () {
    console.log("Loading chat history...")
      $.get('http://localhost:8000/api/chats/history/', (data) => {
        this.chatHistory = data
      })
    console.log("this.chatHistory", this.chatHistory)
    },
    goToSession (uri) {
      this.currentUri = uri;

      this.$router.push({ name: 'Chat', params: { uri } })
      this.joinChatSession()
      this.connectToWebSocket(); // ✅ now will replace old connection

    },
    searchUsers() {
    $.get(`/api/friends/search/?q=${this.searchQuery}`, (data) => {
      this.searchResults = data
    })
  },
    sendFriendRequest(){
      $.post({
        url:'http://localhost:8000/api/friends/request/',
        data: JSON.stringify({username:this.friendUsername}),
        contentType:'application/json',
        success:()=>{ alert('Request sent'); this.showAddFriendModal=false; },
        error:(e)=>alert('Error: '+e.responseText)
      })
    },
    loadFriendRequests(){
      $.get('http://localhost:8000/api/friends/requests/', (data)=>{
        this.friendRequests = data;
      })
    },
    showMailbox(){
      this.loadFriendRequests();
      this.showRequests = true;
    },
    respondRequest(id, action){
      $.post({
        url:'http://localhost:8000/api/friends/respond/',
        data: JSON.stringify({id, action}),
        contentType:'application/json',
        success:(res)=>{
          if(res.chat_uri){
            alert('Friend added! Private chat created.');
            this.loadChatHistory();
          }
          this.loadFriendRequests();
        }
      })
    }
  }

  }
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
h1,
h2 {
  font-weight: normal;
}
ul {
  list-style-type: none;
  padding: 0;
}
li {
  display: inline-block;
  margin: 0 10px;
}

.btn {
  border-radius: 0 !important;
}

.card-footer input[type="text"] {
  background-color: #ffffff;
  color: #444444;
  padding: 7px;
  font-size: 13px;
  border: 2px solid #cccccc;
  width: 100%;
  height: 38px;
}

.card-header a {
  text-decoration: underline;
}

.card-body {
  background-color: #ddd;
}

.chat-body {
  margin-top: -15px;
  margin-bottom: -5px;
  height: 380px;
  overflow-y: auto;
}

.speech-bubble {
  display: inline-block;
  position: relative;
  border-radius: 0.4em;
  padding: 10px;
  background-color: #fff;
  font-size: 14px;
}

.subtle-blue-gradient {
  background: linear-gradient(45deg,#004bff, #007bff);
}

.speech-bubble-user:after {
  content: "";
  position: absolute;
  right: 4px;
  top: 10px;
  width: 0;
  height: 0;
  border: 20px solid transparent;
  border-left-color: #007bff;
  border-right: 0;
  border-top: 0;
  margin-top: -10px;
  margin-right: -20px;
}

.speech-bubble-peer:after {
  content: "";
  position: absolute;
  left: 3px;
  top: 10px;
  width: 0;
  height: 0;
  border: 20px solid transparent;
  border-right-color: #ffffff;
  border-top: 0;
  border-left: 0;
  margin-top: -10px;
  margin-left: -20px;
}

.chat-section:first-child {
  margin-top: 10px;
}

.chat-section {
  margin-top: 15px;
}

.send-section {
  margin-bottom: -20px;
  padding-bottom: 10px;
}

/* Modal Overlay Styles */
.modal-backdrop-custom {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1050;
}

.modal-custom {
  background: white;
  border-radius: 8px;
  padding: 30px;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  animation: modalFadeIn 0.3s ease-out;
}

.modal-custom h5 {
  margin-bottom: 20px;
  color: #333;
  text-align: center;
  font-weight: 600;
}

.modal-custom .form-control {
  margin-bottom: 15px;
  border-radius: 4px;
  border: 1px solid #ddd;
  padding: 10px;
}

.modal-custom .btn {
  margin-right: 10px;
  margin-bottom: 10px;
  border-radius: 4px;
}

.modal-custom .list-group {
  margin-bottom: 20px;
  max-height: 300px;
  overflow-y: auto;
}

.modal-custom .list-group-item {
  border-radius: 4px;
  margin-bottom: 5px;
}

@keyframes modalFadeIn {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
</style>
