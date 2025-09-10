const express = require("express");
const router = express.Router();
const Message = require("../models/Message");

router.get("/:sender/:receiver", async (req, res) => {
  const { sender, receiver } = req.params;
  const msgs = await Message.find({
    $or: [
      { sender, receiver },
      { sender: receiver, receiver: sender }
    ]
  }).sort("timestamp");
  res.json(msgs);
});

module.exports = router;
