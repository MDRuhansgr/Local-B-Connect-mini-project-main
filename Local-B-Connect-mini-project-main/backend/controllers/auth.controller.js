const User = require("../models/User");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");

exports.register = async (req, res) => {
  try {
    const { name, email, password, role } = req.body;

    const existingUser = await User.findOne({ email });
    if (existingUser) return res.status(400).json({ message: "Email already registered" });

    const hashedPassword = await bcrypt.hash(password, 10);

    const user = await User.create({
      name,
      email,
      password: hashedPassword,
      role,
      isVerified: true // Directly mark as verified
    });

    res.status(201).json({ 
      message: "Registration successful. You can now login.",
      email
    });
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
};

// Email verification removed. No longer needed.

exports.login = async (req, res) => {
  const { email, password } = req.body;

  const user = await User.findOne({ email });
  if (!user) return res.status(400).json({ message: "User not found" });

  const isMatch = await bcrypt.compare(password, user.password);
  if (!isMatch) return res.status(400).json({ message: "Incorrect password" });

  // Generate JWT token
  const token = jwt.sign({ id: user._id, role: user.role }, process.env.JWT_SECRET || 'dev-secret-key', {
    expiresIn: "1d",
  });

  res.json({
    token,
    userType: user.role,
    userId: user._id
  });
};

exports.forgotPassword = async (req, res) => {
  return res.status(501).json({ message: "Forgot password feature is disabled." });
};

exports.resetPassword = async (req, res) => {
  return res.status(501).json({ message: "Reset password feature is disabled." });
};
