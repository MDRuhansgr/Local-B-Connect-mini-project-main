const express = require("express");
const router = express.Router();
const serviceController = require("../controllers/service.controller");
const auth = require("../middleware/auth");
const upload = require("../middleware/upload");

router.post("/add", auth, upload.array('photos', 5), serviceController.addService);
router.put("/update/:id", auth, upload.array('photos', 5), serviceController.updateService);
router.delete("/delete/:id", auth, serviceController.deleteService);
router.get("/my", auth, serviceController.myServices);
router.get("/all", serviceController.getAllServices);
router.post("/review/:id", auth, serviceController.addReview);
router.get("/details/:id", serviceController.getServiceDetails);
router.post("/verify", auth, serviceController.verifyService);


module.exports = router;
