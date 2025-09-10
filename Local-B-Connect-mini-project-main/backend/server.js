const express = require("express");
const cors = require("cors");
const mongoose = require("mongoose");
const dotenv = require("dotenv");
const http = require("http");
const { Server } = require("socket.io");
const Message = require("./models/Message");

dotenv.config();
const app = express();

app.use(cors());
app.use(express.json());
app.use("/uploads", express.static("uploads")); // For profile images or service images

// ROUTES
app.use("/api/auth", require("./routes/auth.routes")); // Login/Register
app.use("/api/chat", require("./routes/chat.routes")); // Messaging
//app.use("/api/users", require("./routes/user.routes")); // User profile management
//app.use("/api/providers", require("./routes/provider.routes")); // Service provider profile
app.use("/api/services", require("./routes/service.routes"));
app.use("/api/bookings", require("./routes/booking.routes")); // Services management

//app.use("/api/bookings", require("./routes/booking.routes")); // Appointments/bookings
//app.use("/api/payments", require("./routes/payment.routes")); // Payment logic (e.g., Stripe, Razorpay)
//app.use("/api/ratings", require("./routes/rating.routes")); // User ratings/reviews
//app.use("/api/location", require("./routes/location.routes")); // IP-based geolocation

// DB Connection
mongoose.connect(process.env.MONGO_URI, {
    useNewUrlParser: true,
    useUnifiedTopology: true,
})
.then(() => console.log("MongoDB Connected"))
.catch((err) => console.log("DB Error: ", err));

// HTTP server and Socket.IO
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: "*" }
});

// Socket.io logic
io.on("connection", (socket) => {
  console.log("User connected:", socket.id);

  socket.on("join", (userId) => {
    socket.join(userId);
  });

  socket.on("sendMessage", async ({ sender, receiver, text }) => {
    const newMessage = new Message({ sender, receiver, text });
    await newMessage.save();
    io.to(receiver).emit("receiveMessage", newMessage);
  });

  socket.on("disconnect", () => {
    console.log("User disconnected:", socket.id);
  });
});

// Start server
const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
