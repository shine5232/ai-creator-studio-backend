/*
 Navicat MySQL Data Transfer

 Source Server         : localhost_3306
 Source Server Type    : MySQL
 Source Server Version : 80012
 Source Host           : localhost:3306
 Source Schema         : aigc

 Target Server Type    : MySQL
 Target Server Version : 80012
 File Encoding         : 65001

 Date: 22/04/2026 09:15:31
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ai_models
-- ----------------------------
DROP TABLE IF EXISTS `ai_models`;
CREATE TABLE `ai_models`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `provider_id` int(11) NOT NULL,
  `model_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `model_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `service_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_default` tinyint(1) NOT NULL,
  `config` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `provider_id`(`provider_id`) USING BTREE,
  CONSTRAINT `ai_models_ibfk_1` FOREIGN KEY (`provider_id`) REFERENCES `ai_providers` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of ai_models
-- ----------------------------

-- ----------------------------
-- Table structure for ai_providers
-- ----------------------------
DROP TABLE IF EXISTS `ai_providers`;
CREATE TABLE `ai_providers`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `display_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_enabled` tinyint(1) NOT NULL,
  `config` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of ai_providers
-- ----------------------------

-- ----------------------------
-- Table structure for alembic_version
-- ----------------------------
DROP TABLE IF EXISTS `alembic_version`;
CREATE TABLE `alembic_version`  (
  `version_num` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`version_num`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of alembic_version
-- ----------------------------
INSERT INTO `alembic_version` VALUES ('d030eb8ab794');

-- ----------------------------
-- Table structure for api_keys
-- ----------------------------
DROP TABLE IF EXISTS `api_keys`;
CREATE TABLE `api_keys`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `provider_id` int(11) NOT NULL,
  `encrypted_key` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `key_alias` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `usage_count` int(11) NOT NULL,
  `last_used_at` datetime(0) NULL DEFAULT NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `provider_id`(`provider_id`) USING BTREE,
  CONSTRAINT `api_keys_ibfk_1` FOREIGN KEY (`provider_id`) REFERENCES `ai_providers` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of api_keys
-- ----------------------------

-- ----------------------------
-- Table structure for assets
-- ----------------------------
DROP TABLE IF EXISTS `assets`;
CREATE TABLE `assets`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` int(11) NOT NULL,
  `asset_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `category` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_size` int(11) NULL DEFAULT NULL,
  `mime_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `width` int(11) NULL DEFAULT NULL,
  `height` int(11) NULL DEFAULT NULL,
  `duration` float NULL DEFAULT NULL,
  `metadata` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `shot_id` int(11) NULL DEFAULT NULL,
  `created_at` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `project_id`(`project_id`) USING BTREE,
  INDEX `shot_id`(`shot_id`) USING BTREE,
  CONSTRAINT `assets_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `assets_ibfk_2` FOREIGN KEY (`shot_id`) REFERENCES `shots` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of assets
-- ----------------------------

-- ----------------------------
-- Table structure for character_periods
-- ----------------------------
DROP TABLE IF EXISTS `character_periods`;
CREATE TABLE `character_periods`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `character_id` int(11) NOT NULL,
  `period_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `age` int(11) NULL DEFAULT NULL,
  `appearance_delta` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `clothing_delta` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `expression` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `tone` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `sort_order` int(11) NOT NULL,
  `created_at` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `character_id`(`character_id`) USING BTREE,
  CONSTRAINT `character_periods_ibfk_1` FOREIGN KEY (`character_id`) REFERENCES `characters` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of character_periods
-- ----------------------------
INSERT INTO `character_periods` VALUES (1, 1, '前期', NULL, NULL, '褪色且沾满油污的蓝色工装外套，内穿破损的灰色背心，裤脚卷起沾满泥土', NULL, NULL, 0, '2026-04-19 11:36:22');
INSERT INTO `character_periods` VALUES (2, 1, '中期', NULL, NULL, '同样的工装，但袖口磨破，脸上多了几道新鲜的汗渍和灰尘，神情更加疲惫', NULL, NULL, 1, '2026-04-19 11:36:22');
INSERT INTO `character_periods` VALUES (3, 1, '后期', NULL, NULL, '依旧穿着那件旧工装，但特意拍去了身上的浮尘，胸口别了一朵女儿送的小黄花', NULL, NULL, 2, '2026-04-19 11:36:22');
INSERT INTO `character_periods` VALUES (4, 3, '前期', NULL, NULL, '洗得发白的灰绿色棉质纱丽，搭配深色短袖上衣，赤脚或穿破旧凉鞋', NULL, NULL, 0, NULL);
INSERT INTO `character_periods` VALUES (5, 3, '中期', NULL, NULL, '沾满油污和灰尘的深色工作服，头上裹着防尘头巾，手上戴着破损的橡胶手套', NULL, NULL, 1, NULL);
INSERT INTO `character_periods` VALUES (6, 3, '后期', NULL, NULL, '崭新的粉色丝绸纱丽，边缘绣有金线，佩戴简单的银手镯和耳坠，妆容精致', NULL, NULL, 2, NULL);
INSERT INTO `character_periods` VALUES (7, 4, '前期', NULL, NULL, '褪色且沾满泥点的浅色棉布连衣裙，赤脚，浑身湿透', NULL, NULL, 0, NULL);
INSERT INTO `character_periods` VALUES (8, 4, '中期', NULL, NULL, '简单的居家旧 T 恤和长裤，抱着破旧的泰迪熊', NULL, NULL, 1, NULL);
INSERT INTO `character_periods` VALUES (9, 4, '后期', NULL, NULL, '华丽的金色印度传统舞裙 (Lehenga Choli)，镶嵌亮片和宝石，佩戴脚铃、项链和耳环', NULL, NULL, 2, NULL);

-- ----------------------------
-- Table structure for characters
-- ----------------------------
DROP TABLE IF EXISTS `characters`;
CREATE TABLE `characters`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` int(11) NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `age` int(11) NULL DEFAULT NULL,
  `gender` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `nationality` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `skin_tone` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `ethnic_features` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `appearance` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `personality` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `clothing` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `symbol_meaning` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `reference_image_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `reference_prompt_cn` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `reference_prompt_en` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `project_id`(`project_id`) USING BTREE,
  CONSTRAINT `characters_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of characters
-- ----------------------------
INSERT INTO `characters` VALUES (1, 1, '拉杰什', '主角', 45, '男性', '印度', '古铜色皮肤，质感粗糙，带有明显的日晒痕迹', '', '深黑色瞳孔，眼窝深陷，眼神坚毅且充满慈爱；花白相间的短发，略显凌乱，发质粗硬；高鼻梁，颧骨突出，法令纹深刻，脸型瘦削；身高约170cm，肩膀因长期负重而微驼', '', '', NULL, 'data\\uploads\\char_1_1776650090.png', '拉杰什的人物肖像，男性，45岁，印度，古铜色皮肤，质感粗糙，带有明显的日晒痕迹，深黑色瞳孔，眼窝深陷，眼神坚毅且充满慈爱；花白相间的短发，略显凌乱，发质粗硬；高鼻梁，颧骨突出，法令纹深刻，脸型瘦削；身高约170cm，肩膀因长期负重而微驼，高质量人物肖像，面部细节丰富，电影级光影', 'Character portrait of 拉杰什, 男性, age 45, 深黑色瞳孔，眼窝深陷，眼神坚毅且充满慈爱；花白相间的短发，略显凌乱，发质粗硬；高鼻梁，颧骨突出，法令纹深刻，脸型瘦削；身高约170cm，体型精瘦但肌肉结实，肩膀因长期负重而微驼, wearing 前期: 褪色且沾满油污的蓝色工装外套，内穿破损的灰色背心，裤脚卷起沾满泥土；中期: 同样的工装，但袖口磨破，脸上多了几道新鲜的汗渍和灰尘，神情更加疲惫；后期: 依旧穿着那件旧工装，但特意拍去了身上的浮尘，胸口别了一朵女儿送的小黄花, 双手布满厚茧和多道陈旧疤痕，指关节粗大变形, 古铜色皮肤，质感粗糙，带有明显的日晒痕迹 skin, high quality portrait, detailed face, cinematic lighting', '2026-04-19 11:36:22', '2026-04-20 01:54:50');
INSERT INTO `characters` VALUES (2, 1, '普里娅', '配角', 7, '女性', '印度裔', '肤色较白', NULL, '明亮的大眼睛；扎着两条细长的辫子；瘦小身形', NULL, NULL, NULL, 'data\\uploads\\char_2_1776606447.png', '普里娅的人物肖像，女性，7岁，印度裔，肤色较白，明亮的大眼睛；扎着两条细长的辫子；瘦小身形，高质量人物肖像，面部细节丰富，电影级光影', 'Character portrait of 普里娅, 女性, age 7, 明亮的大眼睛；扎着两条细长的辫子；瘦小身形, 肤色较白 skin, high quality portrait, detailed face, cinematic lighting', '2026-04-19 11:36:22', '2026-04-19 13:47:27');
INSERT INTO `characters` VALUES (3, 2, '萨维特里 (母亲)', NULL, 35, '女性', '南亚裔 (印度/孟加拉国)', '深小麦色皮肤，带有劳作留下的粗糙质感和细微晒斑', '双手布满老茧、烫伤疤痕和因浸泡污水导致的红肿裂口', '深褐色大眼睛，眼窝较深，初期充满焦虑与慈爱，后期眼神坚定且温柔；黑色长发，前期随意盘起略显凌乱，后期梳理整齐并佩戴茉莉花环；高鼻梁，颧骨突出，脸型略瘦削，额间点有红色吉祥痣 (Bindi)；身材瘦弱但线条紧实，因长期负重劳动而微微佝偻，姿态坚韧', '沉默寡言，极度坚韧，无私奉献，为了女儿可以牺牲一切', '前期: 洗得发白的灰绿色棉质纱丽，搭配深色短袖上衣，赤脚或穿破旧凉鞋；中期: 沾满油污和灰尘的深色工作服，头上裹着防尘头巾，手上戴着破损的橡胶手套；后期: 崭新的粉色丝绸纱丽，边缘绣有金线，佩戴简单的银手镯和耳坠，妆容精致', NULL, 'data\\uploads\\char_3_1776796750.png', '一位 35 岁的南亚裔女性，深小麦色皮肤，深褐色大眼睛，高鼻梁，额间点有红色吉祥痣。黑色长发盘起，身穿朴素灰绿色纱丽，双手布满老茧和伤痕，眼神坚毅慈爱。竖屏构图，日式动漫角色设计，精致线条，鲜艳色彩，高质量插画', NULL, '2026-04-21 18:39:01', '2026-04-21 18:39:10');
INSERT INTO `characters` VALUES (4, 2, '米娜 (女儿)', NULL, 8, '女性', '南亚裔 (印度/孟加拉国)', '健康的深棕色皮肤，光滑细腻', '左脚脚踝处有一块小时候留下的淡淡疤痕', '明亮的大黑眼睛，睫毛浓密，初期含泪恐惧，后期自信闪耀；黑色长发，前期编成凌乱的麻花辫，后期梳成精致的发髻并装饰花朵；圆润的脸庞，小巧的鼻子，表情丰富，极具感染力；瘦小纤细，四肢灵活，具有天然的舞蹈体态', '敏感懂事，对舞蹈充满渴望，从自卑怯懦成长为自信耀眼', '前期: 褪色且沾满泥点的浅色棉布连衣裙，赤脚，浑身湿透；中期: 简单的居家旧 T 恤和长裤，抱着破旧的泰迪熊；后期: 华丽的金色印度传统舞裙 (Lehenga Choli)，镶嵌亮片和宝石，佩戴脚铃、项链和耳环', NULL, 'data\\uploads\\char_4_1776796758.png', '一位 8 岁的南亚裔女孩，深棕色皮肤，明亮的大黑眼睛，圆润脸庞。黑色长发编成麻花辫，身穿破旧浅色连衣裙，赤脚，表情委屈。竖屏构图，日式动漫角色设计，精致线条，鲜艳色彩，高质量插画', NULL, '2026-04-21 18:39:01', '2026-04-21 18:39:18');

-- ----------------------------
-- Table structure for content_analytics
-- ----------------------------
DROP TABLE IF EXISTS `content_analytics`;
CREATE TABLE `content_analytics`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` int(11) NOT NULL,
  `publish_record_id` int(11) NULL DEFAULT NULL,
  `platform` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `view_count` int(11) NOT NULL,
  `like_count` int(11) NOT NULL,
  `comment_count` int(11) NOT NULL,
  `share_count` int(11) NOT NULL,
  `favorite_count` int(11) NOT NULL,
  `avg_watch_time` float NULL DEFAULT NULL,
  `engagement_rate` float NULL DEFAULT NULL,
  `recorded_at` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `project_id`(`project_id`) USING BTREE,
  INDEX `publish_record_id`(`publish_record_id`) USING BTREE,
  CONSTRAINT `content_analytics_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `content_analytics_ibfk_2` FOREIGN KEY (`publish_record_id`) REFERENCES `publish_records` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of content_analytics
-- ----------------------------

-- ----------------------------
-- Table structure for generation_costs
-- ----------------------------
DROP TABLE IF EXISTS `generation_costs`;
CREATE TABLE `generation_costs`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` int(11) NULL DEFAULT NULL,
  `user_id` int(11) NULL DEFAULT NULL,
  `provider` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `service_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `shot_id` int(11) NULL DEFAULT NULL,
  `input_tokens` int(11) NULL DEFAULT NULL,
  `output_tokens` int(11) NULL DEFAULT NULL,
  `api_calls` int(11) NOT NULL,
  `cost_amount` float NOT NULL,
  `currency` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `duration_ms` int(11) NULL DEFAULT NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `project_id`(`project_id`) USING BTREE,
  INDEX `shot_id`(`shot_id`) USING BTREE,
  INDEX `user_id`(`user_id`) USING BTREE,
  CONSTRAINT `generation_costs_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `generation_costs_ibfk_2` FOREIGN KEY (`shot_id`) REFERENCES `shots` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `generation_costs_ibfk_3` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of generation_costs
-- ----------------------------

-- ----------------------------
-- Table structure for kb_cases
-- ----------------------------
DROP TABLE IF EXISTS `kb_cases`;
CREATE TABLE `kb_cases`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NULL DEFAULT NULL,
  `platform` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `source_video_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `view_count` int(11) NULL DEFAULT NULL,
  `like_count` int(11) NULL DEFAULT NULL,
  `like_rate` float NULL DEFAULT NULL,
  `duration_seconds` int(11) NULL DEFAULT NULL,
  `uploader` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `upload_date` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `theme` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `narrative_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `narrative_structure` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `story_summary` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `emotion_curve` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `emotion_triggers` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `visual_style` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `visual_contrast` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `viral_elements` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `visual_symbols` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `audience_profile` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `reusable_elements` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `success_factors` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `title_formula` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `characters_ethnicity` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `analysis_report_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `frames_dir` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `analysis_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `analysis_progress` int(11) NULL DEFAULT NULL,
  `celery_task_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `user_id`(`user_id`) USING BTREE,
  CONSTRAINT `kb_cases_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of kb_cases
-- ----------------------------
INSERT INTO `kb_cases` VALUES (1, 1, 'youtube', 'From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 'https://www.youtube.com/shorts/iDkZ0bg0jpc', 'data\\analysis\\youtube\\From_Crippled_Worker_to_Mecha_Overlord!_🤖_The_Bullied_Worker_is_Back_with_Laser_Arms!🦾\\iDkZ0bg0jpc.mp4', 13550645, 143144, NULL, 59, 'Wild Builders Story', '20251220', '逆袭/励志、科幻动作、底层反抗', '线性叙事 + 反转式', '开端（0-15 秒）：展示矿工在昏暗矿井受压迫的艰苦生活，监工指责，氛围压抑；发展（15-30 秒）：突发爆炸事故，矿工重伤被救，陷入生命低谷，情感转为悲痛紧张；高潮（30-45 秒）：医院改造，安装机械义肢，科技实验室升级，情感转为期待与震撼；结局（45-59 秒）：矿工化身机甲战士街头狂奔，面对权贵 confrontation，情感释放为爽感与胜利。', '视频开篇将观众瞬间带入一个压抑且昏暗的地下矿井世界，空气中仿佛弥漫着厚重的煤尘与汗水气息。一名肤色黝黑、留着浓密黑色卷发和络腮胡的年轻矿工，身着沾满泥土污渍的破旧蓝色牛仔衬衫和卡其色短裤，正蹲在满是黑色煤块的地面上艰难劳作。他的肌肉线条在昏黄矿灯下显得紧绷，神情专注却难掩疲惫，手臂上的煤灰见证了繁重的体力劳动。背景中，一名身着白色传统长衫外搭棕色马甲的监工，留着标志性小胡子，正伸出手指严厉指责，奠定了阶级压迫的沉重基调。矿工在简陋工棚吃着粗砺的米饭咖喱，随后手持镐头独自走向黑暗隧道深处，孤独的背影暗示着未知的危险。情节突变，监工手持红色起爆器露出诡异笑容，紧接着画面爆发剧烈爆炸，火光吞噬了黑暗。矿工在废墟中受伤被困，满身血迹，双手撑地痛苦喘息，巨大的岩石悬在头顶，生命危在旦夕。随后他被救援人员紧急抬上担架，胸前血迹斑斑，在尘土飞扬的事故现场被送往医院，情节急转直下进入悲剧低谷，引发观众深切同情。然而，故事并未终结，镜头切换至医院门口，夕阳下矿工奇迹般重生，四肢已替换为木质与金属结合的机械义肢，关节处轴承清晰可见。他身穿病号服，自信地走出急诊室，步伐坚定。在随后的赛博朋克风格巷弄中，冷蓝色调笼罩雨夜，他适应着新身体，用机械手进食面饼，靠在墙边休憩，眼神从疲惫转为坚定，透露出废土生存的坚韧。高科技实验室场景显示他正在接受进一步改造，精密机械臂悬浮校准，全息屏幕闪烁数据。最终，矿工化身机甲战士，脚踏喷射蓝色火焰在街头狂奔，红金相间的机械外骨骼在阳光下闪耀，拥有激光手臂的力量，速度极快。结尾画面回到类似矿场的户外，一位头戴红色头巾、佩戴珍珠项链的富态老者愤怒指责跪地者，暗示着权力的反转或最终的清算。整个故事从底层受虐到机械飞升，完成了从肉体凡胎到机甲领主的华丽逆袭，视觉冲击力极强，情感从压抑到燃爆，层层递进。视频通过强烈的视觉对比，展现了底层劳动者在绝境中寻求力量重生的过程，每一个机械关节的转动都象征着命运的齿轮开始逆转，最终的动作场面更是将情绪推向高潮，给观众带来极大的心理满足感。', '压抑（矿井劳作）→ 绝望（爆炸受伤）→ 期待（机械改造）→ 燃爆（街头狂奔）→ 爽感（权力反转）', '哭点是矿工重伤躺在担架上血迹斑斑的画面，引发对底层命运的同情；燃点是矿工安装机械义肢后自信走出医院及街头喷射奔跑的瞬间，象征力量重生；爽点是结尾面对权贵时的对峙姿态，暗示复仇成功或地位逆转，核心情感为逆袭的快感。', '整体色调从初期的暖黄暗调（矿井）过渡到冷蓝色调（雨夜/医院），最后转为高饱和度的动作暖色调。光影特点为强对比度，初期使用明暗对照法突出压抑感，后期使用霓虹光效和金属反光突出科技感。画面质感兼具现实主义的电影颗粒感与 CGI 特效的光滑金属质感。', '场景对比：昏暗封闭的矿井 vs 开阔明亮的街头/实验室；色彩对比：煤块的黑色/衣服的蓝色 vs 机械臂的红色/火焰的蓝色；服饰对比：破旧脏污的工装 vs 精密高科技外骨骼；人物状态对比：受伤躺担架的虚弱 vs 安装义肢后的强壮奔跑。', '{\"topic_layer\": [\"底层工人逆袭成机甲领主\", \"人体机械改造科幻概念\"], \"emotion_layer\": [\"受压迫后的复仇快感\", \"绝境重生的励志共鸣\"], \"execution_layer\": [\"电影级质感的关键帧画面\", \"快节奏的叙事转折\"]}', '[{\"symbol\": \"煤炭\", \"meaning\": \"象征底层劳役与压迫\"}, {\"symbol\": \"机械义肢\", \"meaning\": \"象征重生与力量觉醒\"}, {\"symbol\": \"爆炸\", \"meaning\": \"象征旧身份的毁灭与新命运的转折\"}, {\"symbol\": \"红色头巾\", \"meaning\": \"象征传统权力与阶级地位\"}]', '核心受众为 18-35 岁男性，喜欢科幻、动作、赛博朋克题材；次要受众为喜欢逆袭爽文叙事的大众用户。他们的情感需求是寻求视觉刺激、渴望看到底层人物通过努力或机遇获得力量从而改变命运的心理补偿。', '{\"narrative_template\": \"受压迫现状 -> 突发灾难/危机 -> 获得外挂/改造 -> 展示力量 -> 反击/胜利\", \"visual_template\": \"暗调现实主义开场 -> 高对比度特效转场 -> 亮调科幻动作收尾\", \"title_formula\": \"从 [初始弱势身份] 到 [最终强势身份]！[核心动作/特征]！\"}', '[\"强烈的视觉反差带来冲击力\", \"经典的逆袭叙事引发情感共鸣\", \"科幻元素与现实题材的结合新颖\", \"节奏紧凑，59 秒内完成完整故事弧光\"]', '身份反差 + 核心卖点 + 情绪感叹号（From [Weak] to [Strong]! [Action]!）', '主角为南亚或中东裔成年男性，肤色深褐，拥有浓密黑色卷发和络腮胡，年龄约 30-40 岁，穿着破旧蓝色工装衬衫和卡其短裤，后期装备红金机械义肢。监工为同种族中年男性，留小胡子，穿白色传统长衫 Kurta 配棕色马甲。救援人员穿卡其色制服。医院外出现的女性为南亚裔，戴眼镜，穿紫色西装。结尾老者戴红色头巾，穿刺绣长袍，佩戴珍珠项链，显示高地位。', 'data\\analysis\\youtube\\From_Crippled_Worker_to_Mecha_Overlord!_🤖_The_Bullied_Worker_is_Back_with_Laser_Arms!🦾\\report.json', 'data\\analysis\\youtube\\From_Crippled_Worker_to_Mecha_Overlord!_🤖_The_Bullied_Worker_is_Back_with_Laser_Arms!🦾/frames', 'completed', 100, '40a8a1ab-7ebf-457a-a96d-d786a3e3da66', '2026-04-19 04:46:53', '2026-04-19 07:09:38');
INSERT INTO `kb_cases` VALUES (3, 1, 'youtube', 'https://www.youtube.com/shorts/JJctiPEUlZA', 'https://www.youtube.com/shorts/JJctiPEUlZA', 'data\\analysis\\youtube\\👩The_Miracle_of_Motherly_Love_Mom\'s_Love_Illuminated_Her_Daughter\'s_Dance_Dream!💃\\JJctiPEUlZA.mp4', NULL, NULL, NULL, 58, NULL, NULL, '逆境重生/母爱伟大/梦想成真', '线性叙事与对比式转折结合', '开端（帧 1-3）：雨夜街头，赤贫女孩遭富人斥责，橱窗金裙形成残酷对比，女孩痛哭，奠定压抑悲情基调；发展（帧 4-12）：母亲出现给予安慰，随后展现母女在简陋家中的相依为命，以及母亲通过街头卖小吃、工地搬砖、后厨洗碗等高强度劳动默默攒钱的艰辛过程，情感由悲伤转为坚韧与期待；高潮（帧 13-14）：母亲拿着辛苦攒下的钱，在橱窗前买下那件象征梦想的金裙，脸上绽放出难以置信的喜悦，实现第一次情感释放；结局（帧 15-19）：女孩收到礼物欣喜若狂，画面转场至伦敦舞蹈节舞台，女孩身着华丽舞衣自信起舞并献花给母亲，完成从底层乞丐到舞台明星的华丽逆袭，情感达到圆满与自豪的顶峰。', '故事始于一个冰冷刺骨的雨夜，繁华都市的街头，一位衣衫褴褛、赤脚站立的南亚裔小女孩，正遭受一名衣着光鲜的白人男子的严厉斥责。男子手指直指女孩额头，姿态傲慢压迫，而女孩身后橱窗内那件闪耀的金色礼服，仿佛在无情嘲笑着她的贫穷与卑微。女孩委屈的泪水混合着雨水滑落，眼神中充满了无助与困惑，这一幕将社会的冷暖不均刻画得入木三分。\n\n就在女孩绝望痛哭之时，她的母亲——一位穿着朴素纱丽的南亚女性，焦急地赶来。她没有言语责备，只是温柔地为女孩撑伞，将她拥入怀中。随后的画面转入她们简陋昏暗的家，女孩抱着破旧泰迪熊入睡，而母亲的眼神中却透着一股不服输的坚毅。为了改变命运，为了给女儿一个梦想，这位母亲开始了近乎自虐般的辛勤劳作：她在烟雾缭绕的街头炸制小吃，双手被油烟熏黑；她在尘土飞扬的工地，用瘦弱的肩膀和头顶承载装满红砖的重筐，每一步都走得艰难沉重；她在冰冷潮湿的后厨，双手浸泡在污水中清洗堆积如山的餐具。每一滴汗水，每一次弯腰，都是为了那个遥不可及的梦想。\n\n转折点发生在母亲终于攒够了钱的那一刻。她再次来到那个曾让她感到卑微的橱窗前，但这次，她手中紧紧攥着一叠皱巴巴却充满分量的钞票。当她买下那件金色礼服时，脸上绽放出的笑容比任何珠宝都耀眼，那是尊严的胜利，是母爱的凯歌。\n\n当女孩接过那份用金色包装纸包裹的礼物时，纯真的快乐瞬间点亮了破旧的房间。故事并未止步于此，镜头一转，时空跨越到了灯火辉煌的“伦敦舞蹈节”舞台。曾经那个赤脚哭泣的小女孩，如今身着华丽的金色传统舞裙，脚踏脚铃，在聚光灯下自信地旋转、跳跃，宛如一只涅槃的金凤凰。台下掌声雷动，她不再是那个被训斥的可怜虫，而是舞台的中心。最后，她手捧鲜花，恭敬地献给台下的母亲，母女俩目光交汇，泪光闪烁。这不仅是一个关于梦想成真的故事，更是一曲母爱战胜贫困、坚韧改写命运的壮丽赞歌。', '压抑委屈（雨夜被骂）→ 悲伤绝望（独自哭泣）→ 温情坚韧（母爱陪伴与劳作）→ 惊喜感动（买下金裙）→ 狂喜纯真（收到礼物）→ 震撼自豪（舞台绽放）', '哭点：帧 3 女孩在雨夜街头无助痛哭，帧 10-12 母亲头顶重砖、双手泡烂洗碗的特写，展现底层生存的极致艰辛；燃点：帧 14 母亲举起钞票买下金裙的瞬间，帧 17 女孩在伦敦舞台聚光灯下旋转的自信身姿；爽点：帧 1 中傲慢男子与帧 17 中舞台主角的身份反差，完成‘昨日你对我爱答不理，今日让你高攀不起’的隐性复仇叙事，满足观众对公平正义和阶层跨越的心理渴望。', '整体色调前期以冷灰蓝为主，营造压抑、寒冷、贫穷的氛围，光影对比强烈，多用侧光和逆光突出人物面部的苦难质感；后期转为暖金黄与绚丽紫蓝，灯光饱满明亮，画面质感从粗糙纪实转向电影级的高饱和度与柔光美化，象征希望与辉煌。', '场景对比：雨夜湿冷街道/简陋厨房 vs 明亮橱窗/宏大舞台；色彩对比：灰暗脏污的衣物 vs 闪耀夺目的金色礼服；人物状态对比：女孩初期的赤脚哭泣、畏缩 vs 后期的盛装起舞、自信微笑；阶级对比：白人男子的傲慢指责 vs 南亚母女的隐忍奋斗与最终成功。', '{\"topic_layer\": [\"贫富差距与社会公平的永恒话题\", \"跨国界通用的母爱与亲情主题\", \"底层小人物逆袭的爽文剧本\"], \"emotion_layer\": [\"极致的悲惨开局引发强烈同情\", \"母亲无声付出的细节戳中泪点\", \"结局华丽反转带来的巨大心理满足\"], \"execution_layer\": [\"电影级的光影运用与构图美学\", \"强烈的视觉符号（金裙）贯穿始终\", \"节奏紧凑，情绪层层递进无尿点\"]}', '[{\"symbol\": \"金色礼服\", \"meaning\": \"象征梦想、希望、社会地位的跃迁以及母爱的具象化\"}, {\"symbol\": \"雨水与泥泞\", \"meaning\": \"象征现实的残酷、生活的困境以及洗涤心灵的苦难\"}, {\"symbol\": \"红砖与汗水\", \"meaning\": \"象征底层劳动者的坚韧、牺牲以及通往成功的基石\"}, {\"symbol\": \"脚铃与舞裙\", \"meaning\": \"象征文化传承、自我价值的实现以及从生存到生活的升华\"}]', '核心受众：来自发展中国家或有过奋斗经历的普通大众，特别是母亲群体和年轻追梦者，他们渴望看到努力改变命运的故事；次要受众：关注社会议题、喜欢感人剧情短片的全年龄段观众，以及对印度文化、舞蹈艺术感兴趣的人群。他们的情感需求是寻求共鸣、获得激励、宣泄对不公的愤怒并体验逆袭的快感。', '{\"narrative_template\": \"极度困境（受辱/贫穷）+ 亲人默默牺牲（高强度劳动蒙太奇）+ 关键道具获取（梦想载体）+ 华丽转身（舞台/成功场景）+ 感恩回馈\", \"visual_template\": \"冷色调压抑开场 -> 暖色调温情过渡 -> 高饱和度辉煌结局，利用同一道具（如衣服）在不同场景下的状态对比制造视觉冲击\", \"title_formula\": \"【强烈反差】+【情感核心】+【结局悬念】，例如：\'雨夜被赶走的赤脚女孩，十年后惊艳伦敦舞台，只因母亲做了这件事...\'\"}', '[\"极具张力的视觉对比，从肮脏贫穷到华丽舞台的跨度极大\", \"精准捕捉人类共通情感：母爱、尊严与梦想，跨越文化隔阂\", \"叙事节奏把控完美，苦难铺垫足够深，使得最后的反转更具爆发力\", \"角色塑造鲜明，母亲的坚韧与女孩的纯真令人印象深刻\", \"符合短视频平台的算法偏好：前 3 秒冲突强烈，中间有泪点，结尾有爽点\"]', '冲突前置 + 情感钩子 + 结果反差（例：\'富人的斥责vs母亲的汗水：赤脚女孩如何穿上金裙登上世界舞台？\'）', '主要人物包括：1. 小女孩：约 6-8 岁，南亚裔（推测为印度或孟加拉国），肤色偏深，黑发编成麻花辫或扎马尾。初期身穿破旧沾泥的浅色连衣裙，赤脚，表情委屈恐惧；后期身穿华丽金色印度传统舞裙（Lehenga Choli），佩戴脚铃和首饰，表情自信灿烂。2. 母亲：约 30-40 岁，南亚裔女性，肤色深，黑发盘起或披肩，额间点有吉祥痣。身穿朴素的灰绿色或褐色纱丽，搭配深色短袖上衣，佩戴简单金银首饰。初期神情焦虑慈爱，中期在劳作中显得疲惫坚毅，后期身穿粉色丝绸纱丽，笑容温柔欣慰。3. 白人男子：约 30-40 岁，高加索人种，身穿整洁白衬衫、卡其裤和皮鞋，姿态傲慢，作为反面配角出现，象征冷漠的权威与阶级壁垒。', 'data\\analysis\\youtube\\👩The_Miracle_of_Motherly_Love_Mom\'s_Love_Illuminated_Her_Daughter\'s_Dance_Dream!💃\\report.json', 'data\\analysis\\youtube\\👩The_Miracle_of_Motherly_Love_Mom\'s_Love_Illuminated_Her_Daughter\'s_Dance_Dream!💃\\frames', 'completed', 100, '2637269f-50bd-4792-804f-0a604bfbb75f', '2026-04-21 04:02:20', '2026-04-21 05:27:46');

-- ----------------------------
-- Table structure for kb_elements
-- ----------------------------
DROP TABLE IF EXISTS `kb_elements`;
CREATE TABLE `kb_elements`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `element_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `impact_score` float NULL DEFAULT NULL,
  `examples` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of kb_elements
-- ----------------------------
INSERT INTO `kb_elements` VALUES (1, 'viral', '惊人的转变', '来自案例: He Turned a Poor Girl\'s Crumbling Room Into an Ocean Palace 🌊✨', 1, '[\"He Turned a Poor Girl\'s Crumbling Room Into an Ocean Palace 🌊✨\"]', '2026-04-18 18:45:26', '2026-04-18 18:45:26');
INSERT INTO `kb_elements` VALUES (2, 'viral', '励志故事', '来自案例: He Turned a Poor Girl\'s Crumbling Room Into an Ocean Palace 🌊✨', 1, '[\"He Turned a Poor Girl\'s Crumbling Room Into an Ocean Palace 🌊✨\"]', '2026-04-18 18:45:26', '2026-04-18 18:45:26');
INSERT INTO `kb_elements` VALUES (3, 'viral', '视觉冲击', '来自案例: He Turned a Poor Girl\'s Crumbling Room Into an Ocean Palace 🌊✨', 1, '[\"He Turned a Poor Girl\'s Crumbling Room Into an Ocean Palace 🌊✨\"]', '2026-04-18 18:45:26', '2026-04-18 18:45:26');
INSERT INTO `kb_elements` VALUES (4, 'visual_symbol', '昏暗的房间→华丽的宫殿', '来自案例: He Turned a Poor Girl\'s Crumbling Room Into an Ocean Palace 🌊✨', 1, '[\"He Turned a Poor Girl\'s Crumbling Room Into an Ocean Palace 🌊✨\"]', '2026-04-18 18:45:26', '2026-04-18 18:45:26');
INSERT INTO `kb_elements` VALUES (5, 'visual_symbol', '破败→重生', '来自案例: He Turned a Poor Girl\'s Crumbling Room Into an Ocean Palace 🌊✨', 1, '[\"He Turned a Poor Girl\'s Crumbling Room Into an Ocean Palace 🌊✨\"]', '2026-04-18 18:45:26', '2026-04-18 18:45:26');
INSERT INTO `kb_elements` VALUES (6, 'visual_symbol', '现实→梦想', '来自案例: He Turned a Poor Girl\'s Crumbling Room Into an Ocean Palace 🌊✨', 1, '[\"He Turned a Poor Girl\'s Crumbling Room Into an Ocean Palace 🌊✨\"]', '2026-04-18 18:45:26', '2026-04-18 18:45:26');
INSERT INTO `kb_elements` VALUES (7, 'viral', '励志故事的反转情节', '来自案例: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-18 20:20:22', '2026-04-18 20:20:22');
INSERT INTO `kb_elements` VALUES (8, 'viral', '机械霸主的视觉冲击', '来自案例: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-18 20:20:22', '2026-04-18 20:20:22');
INSERT INTO `kb_elements` VALUES (9, 'visual_symbol', '矿工的工作服与泥土象征辛苦', '来自案例: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-18 20:20:22', '2026-04-18 20:20:22');
INSERT INTO `kb_elements` VALUES (10, 'visual_symbol', '激光手臂象征力量与胜利', '来自案例: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-18 20:20:22', '2026-04-18 20:20:22');
INSERT INTO `kb_elements` VALUES (11, 'viral_topic_layer', '争议性话题、共鸣性话题、好奇心驱动、悬念标题要素等', '来自案例 [topic_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 2, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 04:51:11', '2026-04-19 04:59:11');
INSERT INTO `kb_elements` VALUES (12, 'viral_emotion_layer', '强烈情感反差、逆袭爽感、正能量结局、情感释放等', '来自案例 [emotion_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 2, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 04:51:11', '2026-04-19 04:59:11');
INSERT INTO `kb_elements` VALUES (13, 'viral_execution_layer', '视觉对比极致、节奏紧凑、核心符号突出、无废话叙事等', '来自案例 [execution_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 2, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 04:51:11', '2026-04-19 04:59:11');
INSERT INTO `kb_elements` VALUES (14, 'viral_topic_layer', '赛博朋克印度风：将高科技机械元素融入南亚底层生活场景，产生强烈的文化碰撞与新奇特感', '来自案例 [topic_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 06:54:46', '2026-04-19 06:54:46');
INSERT INTO `kb_elements` VALUES (15, 'viral_topic_layer', '残疾人逆袭：触碰社会弱势群体话题，通过科幻手段实现身体修复与能力超越，具有普世共鸣', '来自案例 [topic_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 06:54:46', '2026-04-19 06:54:46');
INSERT INTO `kb_elements` VALUES (16, 'viral_emotion_layer', '极致的压抑后释放：前期铺垫足够的苦难，后期力量爆发时能带来更大的心理爽感', '来自案例 [emotion_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 06:54:46', '2026-04-19 06:54:46');
INSERT INTO `kb_elements` VALUES (17, 'viral_emotion_layer', '视觉奇观带来的震撼：高质量的机械特效与火焰特效满足观众对大场面视觉刺激的需求', '来自案例 [emotion_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 06:54:46', '2026-04-19 06:54:46');
INSERT INTO `kb_elements` VALUES (18, 'viral_execution_layer', '节奏紧凑的剪辑：59 秒内完成起承转合，无废话镜头，每一帧都在推动剧情或展示视觉', '来自案例 [execution_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 06:54:46', '2026-04-19 06:54:46');
INSERT INTO `kb_elements` VALUES (19, 'viral_execution_layer', '电影级调色与光影：模仿大片质感，提升视频整体档次，使低成本特效看起来更逼真', '来自案例 [execution_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 06:54:46', '2026-04-19 06:54:46');
INSERT INTO `kb_elements` VALUES (20, 'viral_topic_layer', '底层工人逆袭成机甲领主', '来自案例 [topic_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 07:09:38', '2026-04-19 07:09:38');
INSERT INTO `kb_elements` VALUES (21, 'viral_topic_layer', '人体机械改造科幻概念', '来自案例 [topic_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 07:09:38', '2026-04-19 07:09:38');
INSERT INTO `kb_elements` VALUES (22, 'viral_emotion_layer', '受压迫后的复仇快感', '来自案例 [emotion_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 07:09:38', '2026-04-19 07:09:38');
INSERT INTO `kb_elements` VALUES (23, 'viral_emotion_layer', '绝境重生的励志共鸣', '来自案例 [emotion_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 07:09:38', '2026-04-19 07:09:38');
INSERT INTO `kb_elements` VALUES (24, 'viral_execution_layer', '电影级质感的关键帧画面', '来自案例 [execution_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 07:09:38', '2026-04-19 07:09:38');
INSERT INTO `kb_elements` VALUES (25, 'viral_execution_layer', '快节奏的叙事转折', '来自案例 [execution_layer]: From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾', 1, '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 07:09:38', '2026-04-19 07:09:38');
INSERT INTO `kb_elements` VALUES (26, 'viral_topic_layer', '贫富差距与社会公平的永恒话题', '来自案例 [topic_layer]: https://www.youtube.com/shorts/JJctiPEUlZA', 1, '[\"https://www.youtube.com/shorts/JJctiPEUlZA\"]', '2026-04-21 05:27:46', '2026-04-21 05:27:46');
INSERT INTO `kb_elements` VALUES (27, 'viral_topic_layer', '跨国界通用的母爱与亲情主题', '来自案例 [topic_layer]: https://www.youtube.com/shorts/JJctiPEUlZA', 1, '[\"https://www.youtube.com/shorts/JJctiPEUlZA\"]', '2026-04-21 05:27:46', '2026-04-21 05:27:46');
INSERT INTO `kb_elements` VALUES (28, 'viral_topic_layer', '底层小人物逆袭的爽文剧本', '来自案例 [topic_layer]: https://www.youtube.com/shorts/JJctiPEUlZA', 1, '[\"https://www.youtube.com/shorts/JJctiPEUlZA\"]', '2026-04-21 05:27:46', '2026-04-21 05:27:46');
INSERT INTO `kb_elements` VALUES (29, 'viral_emotion_layer', '极致的悲惨开局引发强烈同情', '来自案例 [emotion_layer]: https://www.youtube.com/shorts/JJctiPEUlZA', 1, '[\"https://www.youtube.com/shorts/JJctiPEUlZA\"]', '2026-04-21 05:27:46', '2026-04-21 05:27:46');
INSERT INTO `kb_elements` VALUES (30, 'viral_emotion_layer', '母亲无声付出的细节戳中泪点', '来自案例 [emotion_layer]: https://www.youtube.com/shorts/JJctiPEUlZA', 1, '[\"https://www.youtube.com/shorts/JJctiPEUlZA\"]', '2026-04-21 05:27:46', '2026-04-21 05:27:46');
INSERT INTO `kb_elements` VALUES (31, 'viral_emotion_layer', '结局华丽反转带来的巨大心理满足', '来自案例 [emotion_layer]: https://www.youtube.com/shorts/JJctiPEUlZA', 1, '[\"https://www.youtube.com/shorts/JJctiPEUlZA\"]', '2026-04-21 05:27:46', '2026-04-21 05:27:46');
INSERT INTO `kb_elements` VALUES (32, 'viral_execution_layer', '电影级的光影运用与构图美学', '来自案例 [execution_layer]: https://www.youtube.com/shorts/JJctiPEUlZA', 1, '[\"https://www.youtube.com/shorts/JJctiPEUlZA\"]', '2026-04-21 05:27:46', '2026-04-21 05:27:46');
INSERT INTO `kb_elements` VALUES (33, 'viral_execution_layer', '强烈的视觉符号（金裙）贯穿始终', '来自案例 [execution_layer]: https://www.youtube.com/shorts/JJctiPEUlZA', 1, '[\"https://www.youtube.com/shorts/JJctiPEUlZA\"]', '2026-04-21 05:27:46', '2026-04-21 05:27:46');
INSERT INTO `kb_elements` VALUES (34, 'viral_execution_layer', '节奏紧凑，情绪层层递进无尿点', '来自案例 [execution_layer]: https://www.youtube.com/shorts/JJctiPEUlZA', 1, '[\"https://www.youtube.com/shorts/JJctiPEUlZA\"]', '2026-04-21 05:27:46', '2026-04-21 05:27:46');

-- ----------------------------
-- Table structure for kb_frameworks
-- ----------------------------
DROP TABLE IF EXISTS `kb_frameworks`;
CREATE TABLE `kb_frameworks`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `framework_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `formula` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `impact_data` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `examples` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of kb_frameworks
-- ----------------------------
INSERT INTO `kb_frameworks` VALUES (1, 'narrative', '反转', '叙事类型: 反转', '压抑→希望→惊喜→感动', '{\"total_cases\": 2, \"avg_like_rate\": 0.0}', '[\"He Turned a Poor Girl\'s Crumbling Room Into an Ocean Palace 🌊✨\", \"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-18 18:45:26', '2026-04-18 20:20:22');
INSERT INTO `kb_frameworks` VALUES (2, 'narrative', '线性叙事', '叙事类型: 线性叙事', '沮丧→期待→兴奋→自豪→圆满', '{\"total_cases\": 2, \"avg_like_rate\": 0.0}', '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 04:51:11', '2026-04-19 04:59:11');
INSERT INTO `kb_frameworks` VALUES (3, 'narrative', '线性叙事 + 对比式转折', '叙事类型: 线性叙事 + 对比式转折', '压抑（矿井劳作）→ 绝望（爆炸受伤）→ 孤独（木质义肢）→ 期待（实验室升级）→ 震撼（火焰奔跑）→ 爽感（面对权贵）', '{\"total_cases\": 1, \"avg_like_rate\": 0}', '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 06:54:46', '2026-04-19 06:54:46');
INSERT INTO `kb_frameworks` VALUES (4, 'narrative', '线性叙事 + 反转式', '叙事类型: 线性叙事 + 反转式', '压抑（矿井劳作）→ 绝望（爆炸受伤）→ 期待（机械改造）→ 燃爆（街头狂奔）→ 爽感（权力反转）', '{\"total_cases\": 1, \"avg_like_rate\": 0}', '[\"From Crippled Worker to Mecha Overlord! 🤖 The Bullied Worker is Back with Laser Arms!🦾\"]', '2026-04-19 07:09:38', '2026-04-19 07:09:38');
INSERT INTO `kb_frameworks` VALUES (5, 'narrative', '线性叙事与对比式转折结合', '叙事类型: 线性叙事与对比式转折结合', '压抑委屈（雨夜被骂）→ 悲伤绝望（独自哭泣）→ 温情坚韧（母爱陪伴与劳作）→ 惊喜感动（买下金裙）→ 狂喜纯真（收到礼物）→ 震撼自豪（舞台绽放）', '{\"total_cases\": 1, \"avg_like_rate\": 0}', '[\"https://www.youtube.com/shorts/JJctiPEUlZA\"]', '2026-04-21 05:27:46', '2026-04-21 05:27:46');

-- ----------------------------
-- Table structure for kb_script_templates
-- ----------------------------
DROP TABLE IF EXISTS `kb_script_templates`;
CREATE TABLE `kb_script_templates`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NULL DEFAULT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `theme` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `narrative_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `duration_seconds` int(11) NULL DEFAULT NULL,
  `template_content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `reference_case_id` int(11) NULL DEFAULT NULL,
  `usage_count` int(11) NOT NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `reference_case_id`(`reference_case_id`) USING BTREE,
  INDEX `user_id`(`user_id`) USING BTREE,
  CONSTRAINT `kb_script_templates_ibfk_1` FOREIGN KEY (`reference_case_id`) REFERENCES `kb_cases` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `kb_script_templates_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of kb_script_templates
-- ----------------------------

-- ----------------------------
-- Table structure for projects
-- ----------------------------
DROP TABLE IF EXISTS `projects`;
CREATE TABLE `projects`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `status` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `source_platform` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `reference_case_id` int(11) NULL DEFAULT NULL,
  `output_duration` int(11) NULL DEFAULT NULL,
  `output_video_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `settings` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `user_id`(`user_id`) USING BTREE,
  CONSTRAINT `projects_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of projects
-- ----------------------------
INSERT INTO `projects` VALUES (1, 1, '父爱', '通过父亲的努力挣钱，为女儿买了一架钢琴', 'completed', NULL, NULL, NULL, 45, 'data\\uploads\\project_1_final_1776628575.mp4', NULL, '2026-04-19 07:49:38', '2026-04-19 19:56:15');
INSERT INTO `projects` VALUES (2, 1, '母爱', '一个关于母亲为了实现女儿舞蹈梦的故事', 'completed', NULL, NULL, 3, 9, 'data\\uploads\\project_2_final_1776796967.mp4', NULL, '2026-04-21 18:18:30', '2026-04-21 18:42:47');

-- ----------------------------
-- Table structure for publish_records
-- ----------------------------
DROP TABLE IF EXISTS `publish_records`;
CREATE TABLE `publish_records`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` int(11) NOT NULL,
  `account_id` int(11) NOT NULL,
  `asset_id` int(11) NULL DEFAULT NULL,
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `tags` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `platform_post_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `platform_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `published_at` datetime(0) NULL DEFAULT NULL,
  `error_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `created_at` datetime(0) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `account_id`(`account_id`) USING BTREE,
  INDEX `asset_id`(`asset_id`) USING BTREE,
  INDEX `project_id`(`project_id`) USING BTREE,
  CONSTRAINT `publish_records_ibfk_1` FOREIGN KEY (`account_id`) REFERENCES `social_accounts` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `publish_records_ibfk_2` FOREIGN KEY (`asset_id`) REFERENCES `assets` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `publish_records_ibfk_3` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of publish_records
-- ----------------------------

-- ----------------------------
-- Table structure for scripts
-- ----------------------------
DROP TABLE IF EXISTS `scripts`;
CREATE TABLE `scripts`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` int(11) NOT NULL,
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `theme` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `sub_theme` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `duration_seconds` int(11) NULL DEFAULT NULL,
  `narrative_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `viral_elements` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `source_case_id` int(11) NULL DEFAULT NULL,
  `script_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `version` int(11) NOT NULL,
  `is_current` tinyint(1) NOT NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `project_id`(`project_id`) USING BTREE,
  CONSTRAINT `scripts_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of scripts
-- ----------------------------
INSERT INTO `scripts` VALUES (1, 1, '油污双手托起黑白琴键', '父爱', NULL, 60, 'emotional', '孟买的雨季总是带着潮湿的闷热，在达拉维贫民窟狭窄的巷弄里，45 岁的拉杰什正佝偻着背，在那台巨大的、锈迹斑斑的废旧机械拆解场中忙碌。他有着典型的印度底层劳工特征：皮肤是长期暴晒后的深古铜色，粗糙得像老树皮，眼窝深陷，那双浑浊却坚定的眼睛里布满了红血丝。他的双手满是黑色的机油和厚厚的老茧，指甲缝里永远洗不净污垢。身上那件褪色的橙色工装背心已被汗水浸透，紧紧贴在瘦骨嶙峋的脊背上。不远处，他 7 岁的女儿米拉正趴在满是灰尘的木箱上，用粉笔在破木板上画着歪歪扭扭的琴键，眼神里透着对远处音乐学校飘出琴声的无限渴望。\n\n日子像生锈的齿轮一样艰难转动。拉杰什每天要搬运比他自己还重的金属部件，每一次肌肉的撕裂感都在提醒他现实的残酷。某天深夜，他在垃圾堆中发现了一台被遗弃的破旧钢琴内部结构，那些断裂的琴弦和发黄的象牙键让他心头一震。他没有丝毫犹豫，当晚就开始行动。接下来的三个月，拉杰什仿佛变成了一个机械魔术师。白天，他加倍劳作，甚至去危险的拆迁现场扛钢筋；晚上，他就在那盏昏黄的煤油灯下，用那双布满伤口的大手，一点点打磨、修复、拼接那些废弃的金属零件。他将粗大的钢管改造成共鸣箱，用精细的锉刀修整每一个琴槌，原本冰冷的废铁在他充满父爱的指尖下逐渐有了温度。他的衣服从完整的工装变成了挂满布条的褴褛衣衫，脸上的皱纹更深了，但眼神却愈发炽热。\n\n终于，在米拉生日的清晨，奇迹发生了。拉杰什掀开盖在角落巨大物体上的脏布，一台由各种废旧机械零件重组而成的“钢铁钢琴”赫然出现在眼前。它虽不如商店里的光亮，却散发着一种粗犷而震撼的美感，阳光透过破屋顶洒在那些打磨得锃亮的金属键上，折射出耀眼的光芒。拉杰什颤抖着伸出那双黑乎乎的大手，轻轻按下第一个键，清脆悦耳的音符瞬间充满了整个破屋。米拉惊呆了，泪水夺眶而出，她扑进父亲怀里，闻着他身上混合着机油与汗水的味道，那是世界上最安心的气息。拉杰什笨拙地抚摸着女儿的头，沙哑地说道：“弹吧，孩子，这是爸爸给你的天空。”那一刻，沉重的机械与轻盈的梦想完美交融，父爱如那座钢铁钢琴般，虽粗糙简陋，却足以承载最华丽的乐章。\n\n---STRUCTURED_DATA---\n{\"character_profiles\": [{\"role_name\": \"拉杰什 (父亲)\", \"age\": 45, \"gender\": \"男性\", \"race_ethnicity\": \"印度裔\", \"skin_color\": \"深古铜色，粗糙且布满晒伤痕迹\", \"eyes\": \"深褐色，眼窝深陷，眼神疲惫但透着坚毅的光芒\", \"hair\": \"黑白相间的短发，略显凌乱，沾有灰尘\", \"facial_features\": \"高鼻梁，颧骨突出，法令纹深邃，下巴留着稀疏的胡茬\", \"body_type\": \"身材消瘦但肌肉紧实，因长期负重而微微驼背\", \"special_marks\": \"双手布满黑色机油渍、烫伤疤痕和厚茧，右眉骨有一道旧伤疤\", \"personality\": \"沉默寡言，坚韧不拔，深沉内敛，对女儿无限宠溺\", \"clothing_phases\": [{\"phase\": \"前期\", \"description\": \"褪色严重的橙色工装背心，破损的灰色长裤，赤脚穿着人字拖\"}, {\"phase\": \"中期\", \"description\": \"沾满油污和汗渍的破烂衬衫，袖口卷起露出受伤的手臂，头上裹着脏头巾\"}, {\"phase\": \"后期\", \"description\": \"洗净但仍陈旧的白色传统库尔塔衫，虽然朴素但整洁，脸上洗去了部分油污\"}]}], \"acts\": [{\"act_number\": 1, \"act_name\": \"尘埃中的向往\", \"time_range\": \"0-15s\", \"shots\": [{\"shot_number\": 1, \"time_range\": \"0-3s\", \"shot_type\": \"特写\", \"location\": \"孟买达拉维贫民窟拆解场\", \"characters\": \"拉杰什（45 岁，深古铜色皮肤，满脸汗水）正用力搬运一块生锈铁板，表情痛苦狰狞\", \"environment\": \"昏暗杂乱，到处是废弃金属，空气中弥漫着尘土，光线压抑灰暗\", \"event\": \"父亲在极度繁重的体力劳动中挣扎\", \"dialog\": \"无（只有沉重的喘息声和金属撞击声）\", \"tone\": \"灰暗冷色调，低饱和度\", \"mood\": \"压抑、艰辛\"}, {\"shot_number\": 2, \"time_range\": \"3-8s\", \"shot_type\": \"中景推近\", \"location\": \"拆解场角落\", \"characters\": \"米拉（7 岁，瘦小，穿着补丁裙）趴在木箱上，手指在空中模拟弹琴，眼神痴迷\", \"environment\": \"背景是巨大的垃圾山，前景是一束微弱的阳光照在女孩脸上\", \"event\": \"女儿模仿弹琴动作，远处传来隐约的钢琴声\", \"dialog\": \"旁白：\\\"她的梦，在垃圾堆里发芽。\\\"\", \"tone\": \"局部暖光，周围冷暗\", \"mood\": \"渴望、反差\"}, {\"shot_number\": 3, \"time_range\": \"8-15s\", \"shot_type\": \"过肩镜头\", \"location\": \"同上\", \"characters\": \"拉杰什停下活计，看着女儿，眼神从疲惫转为坚定，握紧了拳头\", \"environment\": \"夕阳西下，将父女俩的影子拉长，尘埃在光束中飞舞\", \"event\": \"父亲下定决心要改变现状\", \"dialog\": \"无\", \"tone\": \"金红色调，带有希望感\", \"mood\": \"决心、转折\"}]}, {\"act_number\": 2, \"act_name\": \"机械霸主的蜕变\", \"time_range\": \"15-40s\", \"shots\": [{\"shot_number\": 4, \"time_range\": \"15-20s\", \"shot_type\": \"快剪蒙太奇\", \"location\": \"简陋的棚屋内\", \"characters\": \"拉杰什（满脸油污，手臂缠着绷带）在深夜灯光下疯狂打磨金属零件\", \"environment\": \"昏黄煤油灯，四周散落着齿轮、弹簧、钢管，火花四溅\", \"event\": \"父亲利用废旧机械零件开始制作钢琴\", \"dialog\": \"音效：刺耳的打磨声、锤击声节奏化\", \"tone\": \"高对比度，橙黑交织\", \"mood\": \"紧张、专注\"}, {\"shot_number\": 5, \"time_range\": \"20-25s\", \"shot_type\": \"特写\", \"location\": \"工作台\", \"characters\": \"拉杰什粗糙开裂的手指（特写伤痕）小心翼翼地安装一根细小的琴弦\", \"environment\": \"极近距离展示金属质感与皮肤质感的强烈对比\", \"event\": \"精细组装过程，展现“机械霸主”般的掌控力\", \"dialog\": \"无\", \"tone\": \"冷蓝光聚焦在手部\", \"mood\": \"匠心、震撼\"}, {\"shot_number\": 6, \"time_range\": \"25-30s\", \"shot_type\": \"延时摄影\", \"location\": \"棚屋\", \"characters\": \"拉杰什的身影在日夜交替中消瘦，衣服从完整变破烂，但身后的钢琴雏形渐显\", \"environment\": \"光影快速流转，墙上日历被撕去多页\", \"event\": \"时间流逝，努力累积\", \"dialog\": \"旁白：\\\"每一滴汗水，都是音符的代价。\\\"\", \"tone\": \"色彩由暗转亮\", \"mood\": \"坚持、积累\"}, {\"shot_number\": 7, \"time_range\": \"30-35s\", \"shot_type\": \"全景\", \"location\": \"棚屋中央\", \"characters\": \"拉杰什最后敲下一颗铆钉，浑身虚脱地靠在作品旁，露出欣慰笑容\", \"environment\": \"一台由废铁组成的奇特钢琴矗立中央，晨光初现\", \"event\": \"制作完成\", \"dialog\": \"拉杰什（喘息）：\\\"完成了...\\\"\", \"tone\": \"明亮的晨曦金\", \"mood\": \"成就、期待\"}, {\"shot_number\": 8, \"time_range\": \"35-40s\", \"shot_type\": \"特写\", \"location\": \"同上\", \"characters\": \"拉杰什的手轻轻拂过粗糙但闪亮的金属琴键\", \"environment\": \"阳光洒在金属表面，折射出彩虹般的光晕\", \"event\": \"触碰梦想载体\", \"dialog\": \"无\", \"tone\": \"高光溢出，梦幻感\", \"mood\": \"神圣、温柔\"}]}, {\"act_number\": 3, \"act_name\": \"钢铁琴音的绽放\", \"time_range\": \"40-60s\", \"shots\": [{\"shot_number\": 9, \"time_range\": \"40-45s\", \"shot_type\": \"中景\", \"location\": \"棚屋\", \"characters\": \"米拉惊讶地捂住嘴，眼中含泪，看着眼前的“钢铁钢琴”\", \"environment\": \"屋内被打扫干净，阳光充满整个空间\", \"event\": \"女儿发现礼物\", \"dialog\": \"米拉（哽咽）：\\\"爸爸，这是...\\\"\", \"tone\": \"温暖明亮，高饱和度\", \"mood\": \"震惊、感动\"}, {\"shot_number\": 10, \"time_range\": \"45-50s\", \"shot_type\": \"特写组合\", \"location\": \"钢琴前\", \"characters\": \"米拉坐下弹奏，拉杰什站在一旁，黑手与白键（金属键）形成视觉冲击\", \"environment\": \"音符仿佛具象化为光点飞出\", \"event\": \"女儿弹奏出美妙旋律\", \"dialog\": \"音效：清澈动人的钢琴曲《致爱丽丝》变奏版\", \"tone\": \"梦幻金色\", \"mood\": \"释放、升华\"}, {\"shot_number\": 11, \"time_range\": \"50-55s\", \"shot_type\": \"近景\", \"location\": \"同上\", \"characters\": \"拉杰什眼眶湿润，笨拙地抚摸女儿的头，两人相视而笑\", \"environment\": \"背景虚化，焦点在父女情深\", \"event\": \"情感爆发，父爱得到回应\", \"dialog\": \"拉杰什：\\\"弹吧，孩子，这是你的天空。\\\"\", \"tone\": \"柔焦暖调\", \"mood\": \"温馨、幸福\"}, {\"shot_number\": 12, \"time_range\": \"55-60s\", \"shot_type\": \"大远景拉升\", \"location\": \"贫民窟上空\", \"characters\": \"小小的棚屋在广阔的贫民窟中显得渺小，但屋顶闪烁着奇异的光芒\", \"environment\": \"孟买城市天际线为背景，阳光普照\", \"event\": \"画面定格，字幕浮现\", \"dialog\": \"字幕：\\\"父爱，能点石成金。\\\"\", \"tone\": \"宏大辉煌\", \"mood\": \"震撼、余韵\"}]}], \"visual_design\": {\"color_progression\": \"灰暗压抑（贫民窟现实）→ 橙黑高对比（工业制作）→ 金黄梦幻（梦想实现）\", \"contrasts\": [{\"before\": \"肮脏生锈的废弃金属堆\", \"after\": \"闪耀着艺术光芒的钢铁钢琴\", \"symbol\": \"苦难转化为希望的具象化\"}, {\"before\": \"父亲粗糙黑臭的油污双手\", \"after\": \"女儿洁白灵动在琴键上飞舞的手指\", \"symbol\": \"牺牲与传承，卑微托举高贵\"}], \"visual_symbols\": [{\"symbol\": \"生锈的齿轮\", \"meaning\": \"生活的沉重与艰难\"}, {\"symbol\": \"煤油灯下的火花\", \"meaning\": \"父爱燃烧的生命力\"}, {\"symbol\": \"金属钢琴\", \"meaning\": \"在不完美现实中构建的完美梦想\"}]}, \"title_suggestions\": [{\"title\": \"油污双手托起黑白琴键\", \"recommended\": true}, {\"title\": \"废铁堆里的钢琴梦\", \"recommended\": false}, {\"title\": \"印度父亲的机械奇迹\", \"recommended\": false}]}', '[\"惊人的转变\", \"励志故事的反转情节\", \"机械霸主的视觉冲击\", \"视觉冲击\"]', NULL, 'data\\projects\\1\\scripts\\油污双手托起黑白琴键_v1.md', 1, 0, '2026-04-19 08:22:31', '2026-04-19 08:27:26');
INSERT INTO `scripts` VALUES (2, 1, '铁手琴音：孟买父亲的无声誓言', '父爱', NULL, 60, 'emotional', '在孟买拥挤喧嚣的达拉维贫民窟，空气中弥漫着香料与尘土混合的味道。四十五岁的拉杰什，是一位典型的印度底层劳工。他有着深邃如夜的黑眼睛，眼窝深陷，皮肤是被烈日长期暴晒后的古铜色，粗糙得如同老树皮。他的双手布满了厚厚的老茧和几道触目惊心的疤痕，那是常年搬运沉重机械零件留下的勋章。他穿着那件洗得发白、领口松垮的灰色背心，外面套着一件沾满油污的蓝色工装外套，下身是一条磨损严重的深色长裤。每天清晨，当第一缕阳光穿透破旧的铁皮屋顶，拉杰什便开始了他在废料回收站的工作，巨大的机械臂在他身边轰鸣，他却像一颗沉默的螺丝钉，用那双布满伤痕的手，将一个个沉重的金属部件分类、搬运。\n\n在这个充满噪音与尘埃的世界里，拉杰什心中却藏着一个纯净的梦想——为了他七岁的女儿普里娅。普里娅有着一双明亮的大眼睛，皮肤比父亲白皙许多，扎着两条细长的辫子。她常常趴在回收站边缘的铁栅栏上，羡慕地望着远处音乐学校里传出的钢琴声。每当那时，拉杰什停下手中的活计，眼神中会流露出一丝难以察觉的温柔与痛楚。他知道，对于他们这样的家庭，一架钢琴简直是天方夜谭。但他没有说话，只是默默地将每天微薄的收入，小心翼翼地塞进一个生锈的铁盒子里，那是他为女儿存下的希望。\n\n日子一天天过去，拉杰什的手因为过度劳累而更加粗糙，甚至裂开了口子，鲜血渗进掌纹里，他却浑然不觉。他拒绝了工友一起去喝酒解乏的邀请，放弃了所有可能的享受，只为多攒下一枚卢比。终于，在一个洒满金色夕阳的傍晚，拉杰什拖着疲惫的身躯，走进了城里最高档的音乐行。他颤抖着从怀里掏出那个沉甸甸的铁盒子，倒出一堆零碎的硬币和皱巴巴的纸币。店员惊讶地看着这位满身油污的工人，眼中充满了不可思议。拉杰什没有解释，只是用那双粗糙的大手，轻轻抚摸着柜台里那架崭新的白色三角钢琴，仿佛抚摸着世界上最珍贵的宝物。\n\n当那架洁白的钢琴被搬进普里娅狭小却整洁的房间时，整个屋子仿佛被点亮了。普里娅惊喜地捂住嘴巴，眼泪在眼眶里打转。她坐上琴凳，纤细的手指第一次触碰到了黑白琴键。随着第一个音符响起，清澈的旋律瞬间填满了这个破旧的小屋。拉杰什站在门口，身上还穿着那件沾满油污的工装，脸上带着憨厚而满足的笑容。他看着女儿专注的侧脸，听着那如梦似幻的琴声，眼中闪烁着泪光。那一刻，所有的辛劳、汗水乃至伤痛，都化作了这最美的乐章。父爱无声，却如这琴音般，穿透了贫穷与苦难，奏响了生命中最动人的奇迹。', '[\"惊人的转变\", \"励志故事的反转情节\", \"视觉冲击\", \"情感共鸣\"]', NULL, 'data\\projects\\1\\scripts\\铁手琴音孟买父亲的无声誓言_v2.md', 2, 1, '2026-04-19 08:27:26', '2026-04-19 08:46:25');
INSERT INTO `scripts` VALUES (3, 2, '雨夜斥责到舞台中央：母亲用血汗换回女儿的金裙梦', '母爱的力量', NULL, 60, 'emotional', '暴雨如注的伦敦街头，霓虹灯在积水中破碎成光斑。六岁的南亚女孩米娜赤脚站在一家高级舞裙店的橱窗前，雨水顺着她单薄的破旧衣衫滴落。店内，一位衣着考究的白人男子粗暴地挥手驱赶，手指几乎戳到米娜的额头，眼神中满是嫌弃与冷漠。橱窗内那件流光溢彩的金色舞裙，在暖黄灯光下宛如神迹，却无情地嘲笑着米娜的狼狈。米娜委屈的泪水混着雨水滑落，她紧紧攥着衣角，无助地呜咽，仿佛整个世界都抛弃了她。\n\n就在绝望即将吞没小女孩时，一把破旧的黑伞遮住了风雨。母亲萨维特里焦急地赶来，她穿着洗得发白的灰绿色纱丽，额间的吉祥痣在昏暗路灯下显得格外醒目。她没有责备，只是温柔地将米娜拥入怀中，用粗糙却温暖的手掌抚平女儿的颤抖。那一刻，萨维特里的眼神从焦虑转为一种近乎决绝的坚毅。为了女儿眼中的光，她开始了无声的战斗。烟雾缭绕的街头小吃摊前，她被油烟熏得双眼通红，双手布满烫痕；尘土飞扬的建筑工地上，她用瘦弱的肩膀扛起沉重的红砖筐，每一步都踩在泥泞中深深陷落；冰冷刺骨的餐厅后厨，她的双手长期浸泡在污水中洗碗，指关节肿大溃烂。每一滴汗水，每一道伤痕，都是通往梦想的阶梯。\n\n数月后的黄昏，萨维特里再次来到那家橱窗店。她手中紧攥着一叠皱巴巴、带着体温的零钱，那是她无数个日夜拼命的结晶。当店主将那件金色舞裙递给她时，这位从未低头的母亲眼中泛起了泪光，嘴角绽放出比阳光更灿烂的笑容。回到家，米娜拆开金色的包装纸，惊喜的尖叫声瞬间点亮了昏暗的出租屋。她穿上金裙，在狭小的房间里旋转，仿佛已置身舞台。\n\n时光飞逝，镜头转至灯火辉煌的“伦敦国际舞蹈节”。聚光灯下，曾经那个赤脚哭泣的女孩，如今身着华丽的金色传统舞裙，脚踏清脆的脚铃，自信地在舞台中央翩翩起舞。她的每一个旋转都充满了力量与尊严，宛如涅槃的金凤凰。台下掌声雷动，米娜在谢幕时手捧鲜花，目光穿过人群，定格在台下身穿粉色丝绸纱丽的母亲身上。母女对视，泪光闪烁。这不仅是一次表演的成功，更是母爱战胜贫困、坚韧改写命运的壮丽凯歌。\n\n---STRUCTURED_DATA---\n{\"character_profiles\": [{\"role_name\": \"萨维特里 (母亲)\", \"age\": 35, \"gender\": \"女性\", \"race_ethnicity\": \"南亚裔 (印度/孟加拉国)\", \"skin_color\": \"深小麦色皮肤，带有劳作留下的粗糙质感和细微晒斑\", \"eyes\": \"深褐色大眼睛，眼窝较深，初期充满焦虑与慈爱，后期眼神坚定且温柔\", \"hair\": \"黑色长发，前期随意盘起略显凌乱，后期梳理整齐并佩戴茉莉花环\", \"facial_features\": \"高鼻梁，颧骨突出，脸型略瘦削，额间点有红色吉祥痣 (Bindi)\", \"body_type\": \"身材瘦弱但线条紧实，因长期负重劳动而微微佝偻，姿态坚韧\", \"special_marks\": \"双手布满老茧、烫伤疤痕和因浸泡污水导致的红肿裂口\", \"personality\": \"沉默寡言，极度坚韧，无私奉献，为了女儿可以牺牲一切\", \"reference_prompt\": \"一位 35 岁的南亚裔女性，深小麦色皮肤，深褐色大眼睛，高鼻梁，额间点有红色吉祥痣。黑色长发盘起，身穿朴素灰绿色纱丽，双手布满老茧和伤痕，眼神坚毅慈爱。竖屏构图，日式动漫角色设计，精致线条，鲜艳色彩，高质量插画\", \"clothing_phases\": [{\"phase\": \"前期\", \"description\": \"洗得发白的灰绿色棉质纱丽，搭配深色短袖上衣，赤脚或穿破旧凉鞋\"}, {\"phase\": \"中期\", \"description\": \"沾满油污和灰尘的深色工作服，头上裹着防尘头巾，手上戴着破损的橡胶手套\"}, {\"phase\": \"后期\", \"description\": \"崭新的粉色丝绸纱丽，边缘绣有金线，佩戴简单的银手镯和耳坠，妆容精致\"}]}, {\"role_name\": \"米娜 (女儿)\", \"age\": 8, \"gender\": \"女性\", \"race_ethnicity\": \"南亚裔 (印度/孟加拉国)\", \"skin_color\": \"健康的深棕色皮肤，光滑细腻\", \"eyes\": \"明亮的大黑眼睛，睫毛浓密，初期含泪恐惧，后期自信闪耀\", \"hair\": \"黑色长发，前期编成凌乱的麻花辫，后期梳成精致的发髻并装饰花朵\", \"facial_features\": \"圆润的脸庞，小巧的鼻子，表情丰富，极具感染力\", \"body_type\": \"瘦小纤细，四肢灵活，具有天然的舞蹈体态\", \"special_marks\": \"左脚脚踝处有一块小时候留下的淡淡疤痕\", \"personality\": \"敏感懂事，对舞蹈充满渴望，从自卑怯懦成长为自信耀眼\", \"reference_prompt\": \"一位 8 岁的南亚裔女孩，深棕色皮肤，明亮的大黑眼睛，圆润脸庞。黑色长发编成麻花辫，身穿破旧浅色连衣裙，赤脚，表情委屈。竖屏构图，日式动漫角色设计，精致线条，鲜艳色彩，高质量插画\", \"clothing_phases\": [{\"phase\": \"前期\", \"description\": \"褪色且沾满泥点的浅色棉布连衣裙，赤脚，浑身湿透\"}, {\"phase\": \"中期\", \"description\": \"简单的居家旧 T 恤和长裤，抱着破旧的泰迪熊\"}, {\"phase\": \"后期\", \"description\": \"华丽的金色印度传统舞裙 (Lehenga Choli)，镶嵌亮片和宝石，佩戴脚铃、项链和耳环\"}]}], \"acts\": [{\"act_number\": 1, \"act_name\": \"雨夜屈辱\", \"time_range\": \"0-15s\", \"shots\": [{\"shot_number\": 1, \"time_range\": \"0-3s\", \"shot_type\": \"远景 (Long Shot)\", \"location\": \"伦敦繁华街头雨夜\", \"characters\": \"微小的米娜身影孤零零站在雨中\", \"environment\": \"暴雨倾盆，霓虹灯倒影在积水路面，冷色调，压抑氛围\", \"event\": \"大雨冲刷着街道，米娜在橱窗前显得渺小无助\", \"tone\": \"冷灰蓝，高对比度\", \"mood\": \"孤独，寒冷\", \"image_prompt\": \"远景，雨夜的伦敦街头，一个 8 岁南亚女孩米娜独自站在奢侈品店橱窗前，全身湿透，冷灰蓝色调，霓虹灯反射在积水路面，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"大雨倾盆而下，路面积水泛起涟漪，女孩在风中微微颤抖，镜头缓慢推进\"}, {\"shot_number\": 2, \"time_range\": \"3-6s\", \"shot_type\": \"中景 (Medium Shot)\", \"location\": \"舞裙店橱窗外\", \"characters\": \"白人男子愤怒指责，米娜畏缩后退\", \"environment\": \"明亮的橱窗内展示着金色舞裙，与外部黑暗形成强烈对比\", \"event\": \"男子手指指着米娜额头驱赶，米娜害怕地后退\", \"tone\": \"冷暖对比强烈\", \"mood\": \"冲突，压迫\", \"image_prompt\": \"中景，衣着光鲜的白人男子愤怒地指着 8 岁南亚女孩米娜，女孩畏缩后退，身后橱窗内金色舞裙闪耀，冷暖光对比，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"男子手指向前伸出，女孩身体后仰，雨水顺着脸颊滑落，镜头轻微晃动表现紧张感\"}, {\"shot_number\": 3, \"time_range\": \"6-9s\", \"shot_type\": \"特写 (Close-up)\", \"location\": \"米娜的面部\", \"characters\": \"米娜泪流满面，眼神绝望\", \"environment\": \"背景虚化，只有雨水和模糊的灯光\", \"event\": \"泪水混合雨水从米娜眼中涌出，嘴唇颤抖\", \"tone\": \"暗蓝色，柔焦\", \"mood\": \"悲伤，心碎\", \"image_prompt\": \"特写，8 岁南亚女孩米娜的脸部，泪水混合雨水滑落，眼神充满绝望和无助，背景虚化，暗蓝色调，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"眼泪大颗滚落，女孩眨眼，雨水打在睫毛上，微距镜头捕捉表情细节\"}, {\"shot_number\": 4, \"time_range\": \"9-12s\", \"shot_type\": \"中近景 (Medium Close-up)\", \"location\": \"街头雨中\", \"characters\": \"母亲萨维特里撑伞出现，拥抱米娜\", \"environment\": \"一把破旧黑伞遮住两人，周围依然是冷雨\", \"event\": \"母亲焦急跑来，将米娜紧紧抱在怀里安慰\", \"tone\": \"略微转暖的灰色\", \"mood\": \"温情，依靠\", \"image_prompt\": \"中近景，35 岁南亚母亲萨维特里撑着破伞抱住哭泣的女儿米娜，母亲神情焦虑又慈爱，雨夜街头，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"母亲快速入画，张开双臂拥抱，雨伞在风中倾斜，镜头跟随动作移动\"}, {\"shot_number\": 5, \"time_range\": \"12-15s\", \"shot_type\": \"特写 (Close-up)\", \"location\": \"母亲的眼神\", \"characters\": \"萨维特里看着橱窗内的金裙，眼神变得坚定\", \"environment\": \"瞳孔中倒映着金色舞裙的光芒\", \"event\": \"母亲咬紧牙关，眼神从心疼转为决绝\", \"tone\": \"眼中有一点金光\", \"mood\": \"决心，誓言\", \"image_prompt\": \"特写，35 岁南亚母亲萨维特里的眼睛，瞳孔中倒映着金色舞裙的光芒，眼神从悲伤转为坚定，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"眼球微微转动，瞳孔中的金光闪烁，睫毛颤动，表现内心活动\"}]}, {\"act_number\": 2, \"act_name\": \"血汗筑梦\", \"time_range\": \"15-40s\", \"shots\": [{\"shot_number\": 6, \"time_range\": \"15-18s\", \"shot_type\": \"全景 (Full Shot)\", \"location\": \"简陋昏暗的出租屋\", \"characters\": \"米娜抱着泰迪熊睡在地板上，母亲在角落数零钱\", \"environment\": \"墙壁斑驳，只有一盏昏黄灯泡，气氛清贫\", \"event\": \"母亲在微光下仔细整理皱巴巴的硬币和纸币\", \"tone\": \"昏黄，低饱和度\", \"mood\": \"艰辛，期盼\", \"image_prompt\": \"全景，简陋出租屋内，8 岁女孩米娜睡在地板垫子上，35 岁母亲萨维特里在角落昏黄灯光下数零钱，墙壁斑驳，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"母亲手指轻轻捻过纸币，灯光摇曳，女孩呼吸起伏，固定镜头\"}, {\"shot_number\": 7, \"time_range\": \"18-21s\", \"shot_type\": \"中景 (Medium Shot)\", \"location\": \"街头小吃摊\", \"characters\": \"萨维特里在油锅前忙碌，满脸油烟\", \"environment\": \"烟雾缭绕，火光映照，环境嘈杂脏乱\", \"event\": \"母亲被热油溅到手，皱眉忍耐，继续翻炒食物\", \"tone\": \"橙红与黑灰交织\", \"mood\": \"煎熬，坚持\", \"image_prompt\": \"中景，35 岁南亚母亲萨维特里在街头小吃摊炸食物，脸上沾满油烟，被热油溅到后忍痛继续工作，火光映照，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"油锅沸腾冒烟，母亲手部动作迅速，火焰升腾，镜头轻微推近\"}, {\"shot_number\": 8, \"time_range\": \"21-24s\", \"shot_type\": \"低角度仰拍 (Low Angle)\", \"location\": \"建筑工地\", \"characters\": \"萨维特里头顶重砖筐，步履蹒跚\", \"environment\": \"尘土飞扬，钢筋水泥林立，阳光刺眼\", \"event\": \"母亲扛着沉重的红砖，汗水如雨下，双腿颤抖\", \"tone\": \"土黄色，高对比度\", \"mood\": \"沉重，负荷\", \"image_prompt\": \"低角度仰拍，35 岁南亚母亲萨维特里头顶装满红砖的筐，在建筑工地艰难行走，尘土飞扬，汗水直流，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"母亲脚步沉重踏起灰尘，身体因负重而摇晃，镜头跟随脚步移动\"}, {\"shot_number\": 9, \"time_range\": \"24-27s\", \"shot_type\": \"特写 (Close-up)\", \"location\": \"餐厅后厨水槽\", \"characters\": \"萨维特里红肿溃烂的双手在污水中洗碗\", \"environment\": \"冰冷的水，堆积如山的脏盘子，阴暗潮湿\", \"event\": \"双手用力搓洗盘子，伤口接触冷水产生刺痛感\", \"tone\": \"青灰色，冷光\", \"mood\": \"痛苦，牺牲\", \"image_prompt\": \"特写，35 岁南亚母亲萨维特里红肿溃烂的双手在冰冷污水中清洗脏盘子，伤口清晰可见，青灰色调，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"水流冲刷双手，手指因疼痛而蜷缩又伸直，泡沫破裂，微距镜头\"}, {\"shot_number\": 10, \"time_range\": \"27-30s\", \"shot_type\": \"蒙太奇快切 (Montage)\", \"location\": \"多个劳动场景\", \"characters\": \"母亲在不同场景中疲惫的身影\", \"environment\": \"快速切换的工地、厨房、街头\", \"event\": \"时间流逝，母亲的白发增多，背更驼，但手中的钱变多\", \"tone\": \"节奏明快，色彩随场景变化\", \"mood\": \"紧迫，积累\", \"image_prompt\": \"蒙太奇画面，35 岁南亚母亲萨维特里在工地、厨房、街头劳作的快速剪辑，表情日益疲惫但眼神坚定，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"画面快速闪回，动作连贯，配合时钟转动特效，表现时间流逝\"}, {\"shot_number\": 11, \"time_range\": \"30-33s\", \"shot_type\": \"特写 (Close-up)\", \"location\": \"存钱罐/手帕\", \"characters\": \"一叠厚厚的零钱\", \"environment\": \"粗糙的手掌上托着来之不易的积蓄\", \"event\": \"母亲将最后一枚硬币放入，握紧拳头\", \"tone\": \"暖金色光晕\", \"mood\": \"希望，达成\", \"image_prompt\": \"特写，35 岁南亚母亲萨维特里粗糙的手掌托着一叠皱巴巴的零钱，暖金色光晕笼罩，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"手指轻轻合拢握住钱币，光线在指缝间闪烁，镜头缓慢拉远\"}, {\"shot_number\": 12, \"time_range\": \"33-36s\", \"shot_type\": \"中景 (Medium Shot)\", \"location\": \"舞裙店门口 (白天)\", \"characters\": \"萨维特里整理衣角，深吸一口气走进去\", \"environment\": \"阳光明媚，店铺玻璃干净明亮\", \"event\": \"母亲鼓起勇气，推开那扇曾经让她自卑的门\", \"tone\": \"明亮自然光\", \"mood\": \"勇敢，转折\", \"image_prompt\": \"中景，35 岁南亚母亲萨维特里穿着整洁的纱丽，在白天阳光下深吸一口气，推开舞裙店的玻璃门，明亮自然光，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"门被推开，风铃作响，母亲迈步进入，镜头跟随背影\"}, {\"shot_number\": 13, \"time_range\": \"36-40s\", \"shot_type\": \"中近景 (Medium Close-up)\", \"location\": \"店内柜台前\", \"characters\": \"萨维特里递出钱，店员递出金裙\", \"environment\": \"店内豪华，金色舞裙在灯光下熠熠生辉\", \"event\": \"交易完成，母亲双手接过金裙，脸上露出难以置信的喜悦\", \"tone\": \"璀璨金黄\", \"mood\": \"狂喜，释放\", \"image_prompt\": \"中近景，35 岁南亚母亲萨维特里双手接过华丽的金色舞裙，脸上绽放出灿烂喜悦的笑容，店内灯光璀璨，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"母亲笑容展开，眼中含泪，金裙在手中抖动发出光芒，镜头环绕\"}]}, {\"act_number\": 3, \"act_name\": \"金色涅槃\", \"time_range\": \"40-60s\", \"shots\": [{\"shot_number\": 14, \"time_range\": \"40-43s\", \"shot_type\": \"中景 (Medium Shot)\", \"location\": \"简陋家中\", \"characters\": \"米娜打开礼物，惊喜尖叫\", \"environment\": \"破旧房间被金裙的光芒照亮\", \"event\": \"米娜穿上金裙，在狭小空间里快乐旋转\", \"tone\": \"温馨暖黄\", \"mood\": \"纯真，幸福\", \"image_prompt\": \"中景，8 岁南亚女孩米娜在破旧家中打开礼物，穿上金色舞裙快乐旋转，房间被金光照亮，温馨暖黄调，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"女孩原地旋转，裙摆飞扬，脸上洋溢着纯粹的快乐，镜头跟随旋转\"}, {\"shot_number\": 15, \"time_range\": \"43-46s\", \"shot_type\": \"大远景 (Extreme Long Shot)\", \"location\": \"伦敦舞蹈节舞台\", \"characters\": \"舞台上渺小的身影逐渐变大\", \"environment\": \"宏大的剧院，座无虚席，聚光灯汇聚\", \"event\": \"幕布拉开，灯光聚焦\", \"tone\": \"深蓝背景，金色光束\", \"mood\": \"宏大，期待\", \"image_prompt\": \"大远景，宏大的伦敦舞蹈节剧院舞台，聚光灯汇聚在中央，观众席黑暗中人头攒动，深蓝背景金色光束，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"幕布缓缓拉开，聚光灯亮起，镜头从高空俯冲向下\"}, {\"shot_number\": 16, \"time_range\": \"46-49s\", \"shot_type\": \"全景 (Full Shot)\", \"location\": \"舞台中央\", \"characters\": \"米娜身着金裙，自信起舞\", \"environment\": \"绚丽的舞台灯光，梦幻的背景\", \"event\": \"米娜做出高难度舞蹈动作，脚铃清脆作响\", \"tone\": \"绚丽紫蓝与金黄\", \"mood\": \"震撼，华丽\", \"image_prompt\": \"全景，8 岁南亚女孩米娜身着华丽金色舞裙在舞台中央自信起舞，动作优美，脚铃闪烁，绚丽紫蓝与金黄色调，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"女孩高高跃起旋转，裙摆如花绽放，光效粒子飞舞，慢动作镜头\"}, {\"shot_number\": 17, \"time_range\": \"49-52s\", \"shot_type\": \"特写 (Close-up)\", \"location\": \"米娜的面部\", \"characters\": \"米娜自信微笑，汗水闪光\", \"environment\": \"背景是模糊的观众和灯光\", \"event\": \"米娜眼神坚定，展现出与雨夜截然不同的自信\", \"tone\": \"高光，柔焦\", \"mood\": \"自信，荣耀\", \"image_prompt\": \"特写，8 岁南亚女孩米娜在舞台上的面部特写，自信灿烂的微笑，汗水在灯光下闪光，眼神坚定，高光柔焦，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"女孩转头面向观众，笑容绽放，头发随风飘动，镜头缓慢推近\"}, {\"shot_number\": 18, \"time_range\": \"52-55s\", \"shot_type\": \"中景 (Medium Shot)\", \"location\": \"舞台边缘/观众席第一排\", \"characters\": \"米娜献花给母亲萨维特里\", \"environment\": \"舞台边缘，母亲身穿粉色纱丽起身\", \"event\": \"米娜跑向母亲，献上鲜花，两人紧紧相拥\", \"tone\": \"温暖粉红\", \"mood\": \"感恩，深情\", \"image_prompt\": \"中景，8 岁女孩米娜在舞台边缘将鲜花献给身穿粉色纱丽的母亲萨维特里，两人紧紧相拥，温暖粉色调，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"女孩奔跑，递花，母亲弯腰拥抱，花瓣飘落，镜头横向跟随\"}, {\"shot_number\": 19, \"time_range\": \"55-58s\", \"shot_type\": \"特写 (Close-up)\", \"location\": \"母女对视\", \"characters\": \"母女二人泪光闪烁，笑容温暖\", \"environment\": \"背景虚化成光斑\", \"event\": \"母女目光交汇，无需言语的默契与感动\", \"tone\": \"极致暖光\", \"mood\": \"圆满，感动\", \"image_prompt\": \"特写，8 岁女孩米娜和 35 岁母亲萨维特里对视，眼中含泪面带微笑，背景虚化成光斑，极致暖光，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"两人眼神交流，泪水在眼眶打转，嘴角上扬，镜头静止聚焦情感\"}, {\"shot_number\": 20, \"time_range\": \"58-60s\", \"shot_type\": \"远景 (Long Shot)\", \"location\": \"舞台全景\", \"characters\": \"母女牵手向观众致意\", \"environment\": \"全场掌声，彩带飘落，灯光辉煌\", \"event\": \"画面定格在母女牵手的剪影，字幕浮现\", \"tone\": \"辉煌多彩\", \"mood\": \"升华，希望\", \"image_prompt\": \"远景，舞台全景，8 岁女孩米娜和 35 岁母亲萨维特里牵手向观众致意，彩带飘落，灯光辉煌，辉煌多彩色调，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16\", \"video_prompt\": \"彩带漫天飞舞，灯光闪烁，镜头缓缓拉远直至黑屏，结束\"}]}], \"visual_design\": {\"color_progression\": \"冷灰蓝 (压抑雨夜) → 昏黄/土黄/青灰 (艰辛劳作) → 璀璨金黄/绚丽紫蓝 (舞台辉煌)\", \"contrasts\": [{\"before\": \"雨夜街头赤脚哭泣的卑微女孩\", \"after\": \"聚光灯下盛装起舞的自信明星\", \"symbol\": \"阶层跨越与自我价值的实现\"}, {\"before\": \"母亲粗糙溃烂的双手与破旧纱丽\", \"after\": \"母亲手中闪耀的金裙与粉色丝绸纱丽\", \"symbol\": \"牺牲与回报，苦难孕育辉煌\"}], \"visual_symbols\": [{\"symbol\": \"金色舞裙\", \"meaning\": \"梦想的具体化，母爱的结晶，社会地位跃迁的象征\"}, {\"symbol\": \"雨水与泥泞\", \"meaning\": \"现实的残酷阻碍，洗涤心灵的苦难历程\"}, {\"symbol\": \"脚铃\", \"meaning\": \"文化的传承，从生存挣扎到艺术追求的升华\"}]}, \"title_suggestions\": [{\"title\": \"雨夜斥责到舞台中央：母亲用血汗换回女儿的金裙梦\", \"recommended\": true}, {\"title\": \"从被驱赶到万众瞩目：一件金裙背后的母爱奇迹\", \"recommended\": false}, {\"title\": \"她洗净千万个碗，只为女儿穿上那件金色舞裙\", \"recommended\": false}]}', '[\"惊人的转变\", \"励志故事\", \"视觉冲击\", \"励志故事的反转情节\", \"极致的悲惨开局引发强烈同情\", \"母亲无声付出的细节戳中泪点\"]', 3, 'data\\projects\\2\\scripts\\雨夜斥责到舞台中央母亲用血汗换回女儿的金裙梦_v1.md', 1, 1, '2026-04-21 18:39:01', '2026-04-21 18:39:01');

-- ----------------------------
-- Table structure for shots
-- ----------------------------
DROP TABLE IF EXISTS `shots`;
CREATE TABLE `shots`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `storyboard_id` int(11) NOT NULL,
  `shot_number` int(11) NOT NULL,
  `act_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `time_range` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `shot_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `tone` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `mood` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `dialog` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `dialog_lang` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `image_prompt` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `image_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `image_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `image_task_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `video_prompt` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `video_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `video_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `video_task_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `video_duration` float NOT NULL,
  `video_provider` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `video_model` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `storyboard_id`(`storyboard_id`) USING BTREE,
  CONSTRAINT `shots_ibfk_1` FOREIGN KEY (`storyboard_id`) REFERENCES `storyboards` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of shots
-- ----------------------------
INSERT INTO `shots` VALUES (1, 1, 1, '尘埃中的仰望', '0-3s', '特写', '人物: 拉杰什（45 岁，古铜色皮肤，满脸汗水）正用布满老茧和伤疤的双手搬运沉重的齿轮，表情痛苦但坚定；环境: 昏暗嘈杂的回收站，漫天飞舞的金属粉尘，背景是巨大的生锈机械臂，光线压抑呈灰黄色；事件: 拉杰什咬牙搬起重物，汗水滴落在金属上', '灰黄暗沉，高对比度噪点', '压抑、艰辛', NULL, NULL, '特写镜头，45 岁印度裔男性拉杰什，古铜色粗糙皮肤带有明显日晒痕迹，深黑色瞳孔深陷于眼窝中，眼神坚毅且充满慈爱，花白相间的凌乱短发，发质粗硬，高鼻梁，颧骨突出，法令纹深刻，脸型瘦削，体型精瘦肌肉结实，肩膀微驼，双手布满厚茧和多道陈旧疤痕，指关节粗大变形；身穿褪色且沾满油污的蓝色工装外套，内穿破损的灰色背心；正用那双布满老茧和伤疤的双手死死搬起沉重的金属齿轮，面部因极度用力而扭曲，表情痛苦但目光坚定，满头大汗，汗珠顺着脸颊滑落滴在金属上；身处昏暗嘈杂的孟买回收站，漫天飞舞的金属粉尘，背景隐约可见巨大的生锈机械臂，光线压抑呈灰黄色；灰黄暗沉色调，高对比度噪点，戏剧性侧光，紧凑构图，压抑艰辛氛围，电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_1_1776615882.png', 'completed', NULL, '拉杰什咬紧牙关搬起沉重齿轮，面部肌肉因极度用力而剧烈颤抖，汗珠顺着脸颊滑落滴在金属上；昏暗回收站中金属粉尘漫天飞舞，背景生锈机械臂在压抑的灰黄光线下若隐若现；镜头微距特写并伴随轻微手持晃动，捕捉汗水滴落的瞬间，营造艰辛压抑的电影质感。', 'data\\uploads\\shot_1_video_1776625713.mp4', 'completed', '6a40220c-0d0e-4094-a072-9f063f5579cd', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:08:33');
INSERT INTO `shots` VALUES (2, 1, 2, '尘埃中的仰望', '3-6s', '中景', '人物: 普里娅（7 岁，肤色较白，大眼睛）趴在栅栏上，眼神渴望地望向远方；拉杰什在背景中停下动作凝视女儿；环境: 铁栅栏锈迹斑斑，远处隐约可见豪华音乐学校的尖顶，冷暖色调分割明显；事件: 父女隔空对视，父亲眼神瞬间柔和', '前景冷蓝，背景暖黄', '渴望、无奈', NULL, NULL, '中景镜头，画面主体为 7 岁印度裔女孩普里娅，肤色较白，拥有明亮的大眼睛，扎着两条细长的辫子，身形瘦小，正趴在锈迹斑斑的铁栅栏上，眼神充满渴望地望向远方；背景中是 45 岁的印度男性拉杰什，古铜色粗糙皮肤带有明显日晒痕迹，深黑色瞳孔，眼窝深陷，花白相间的凌乱短发，高鼻梁，颧骨突出，法令纹深刻，脸型瘦削，肩膀微驼，他停下动作凝视着女儿，眼神瞬间变得柔和慈爱。环境位于户外，前景是冰冷的铁栅栏，远处隐约可见豪华音乐学校的尖顶，冷暖色调分割明显，前景笼罩在冷蓝色调中，背景沐浴在暖黄色光线下，空气中仿佛飘来断续的钢琴声。色彩对比强烈，光影戏剧化，对角线构图，氛围充满渴望与无奈。电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_2_1776615940.png', 'completed', NULL, '普里娅趴在栅栏上微微抬头，拉杰什在背景中停下动作凝视女儿，眼神瞬间由坚毅转为柔和慈爱。镜头缓慢推进聚焦父女隔空对视的瞬间，前景冷蓝与背景暖黄的光影随微风轻轻流动。电影感写实风格，氛围充满渴望与无奈。', 'data\\uploads\\shot_2_video_1776625841.mp4', 'completed', 'b58ab8cf-9780-4550-9f94-2e20999bf12a', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:10:41');
INSERT INTO `shots` VALUES (3, 1, 3, '尘埃中的仰望', '6-9s', '特写', '人物: 拉杰什的手部特写，将一枚沾血的硬币放入生锈铁盒，手指微微颤抖；环境: 昏暗的屋内，仅有一盏昏黄灯泡，墙上贴着女儿画的钢琴涂鸦；事件: 存钱动作，铁盒里硬币碰撞声清脆', '暖黄微弱，阴影浓重', '隐忍、希望', NULL, NULL, '特写镜头，画面主体为拉杰什布满厚茧和多道陈旧疤痕的双手，指关节粗大变形，古铜色皮肤质感粗糙且带有明显日晒痕迹，正将一枚沾血的硬币放入生锈铁盒中，手指因用力或疲惫而微微颤抖；环境位于昏暗的屋内，仅有一盏昏黄灯泡提供光源，背景虚化处可见墙上贴着女儿画的钢琴涂鸦，空气中漂浮着微尘；色调暖黄微弱，阴影浓重，高对比度光影，局部照明，构图聚焦手部细节与铁盒，氛围隐忍且充满希望；电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_3_1776616017.png', 'completed', NULL, '拉杰什布满老茧的双手将沾血硬币放入生锈铁盒，手指因疲惫微微颤抖；昏黄灯泡下尘埃在光束中缓缓浮动，墙上钢琴涂鸦在阴影中若隐若现；镜头极缓慢推进聚焦硬币落入瞬间，光影随手部动作产生细微明暗变化；电影感写实风格，氛围隐忍而充满希望。', 'data\\uploads\\shot_3_video_1776625887.mp4', 'completed', '60c2e5ec-7b77-4f19-8708-4d520fa63135', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:11:27');
INSERT INTO `shots` VALUES (4, 1, 4, '尘埃中的仰望', '9-12s', '快剪蒙太奇', '人物: 拉杰什在不同时间段的劳作身影，面容日益憔悴，手上的伤口增多；环境: 烈日下的工地、雨中的街道、深夜的仓库，光影快速切换；事件: 时间流逝，父亲拼命工作', '色彩饱和度逐渐降低，体现疲惫', '紧迫、牺牲', NULL, NULL, '特写与中景快速切换的蒙太奇画面，主体为 45 岁印度男性拉杰什，拥有古铜色且质感粗糙的皮肤，带有明显日晒痕迹，深黑色瞳孔深陷于眼窝，眼神从坚毅逐渐转为疲惫但依旧充满慈爱，花白相间的短发凌乱粗硬，高鼻梁，颧骨突出，法令纹深刻，瘦削脸型，身高约 170cm，肩膀因长期负重而微驼；画面展现他在不同时间段的劳作状态，面容日益憔悴，双手布满增多的伤口与老茧，表情在烈日灼烧下的痛苦、雨水中冲刷的麻木与深夜里的坚忍间快速变换，情绪充满牺牲感与紧迫性；背景在烈日暴晒尘土飞扬的工地、暴雨倾盆的孟买街道、昏暗压抑的深夜仓库之间极速流转，光线从刺眼的强光变为阴冷的雨光再到昏黄的灯光快速切换；色彩饱和度随时间推移逐渐降低，低对比度光影，动态模糊构图，压抑沉重的氛围；电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_4_1776616484.png', 'completed', NULL, '拉杰什在不同场景中劳作，面容日益憔悴且伤口增多。背景在烈日工地、雨中街道与深夜仓库间极速切换，光线由刺眼强光转为阴冷雨光再变昏黄灯光。色彩饱和度随时间推移逐渐降低，镜头快速剪辑配合动态模糊，营造紧迫牺牲的电影感氛围。', 'data\\uploads\\shot_4_video_1776626012.mp4', 'completed', 'de00854a-5681-469b-9b2a-b88cf033f171', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:13:32');
INSERT INTO `shots` VALUES (5, 1, 5, '尘埃中的仰望', '12-15s', '近景', '人物: 拉杰什（衣衫褴褛）站在光鲜亮丽的橱窗前，显得格格不入，眼神却异常明亮；环境: 明亮的商店橱窗，反射出繁华街道，与父亲的落魄形成强烈反差；事件: 父亲深吸一口气，推门而入；', '外部冷白，内部暖金', '决绝、期待', NULL, NULL, '近景镜头，画面主体为 45 岁印度男性拉杰什，古铜色粗糙皮肤带有明显日晒痕迹，深黑色瞳孔深陷，眼神坚毅且充满慈爱，花白相间的短发略显凌乱且发质粗硬，高鼻梁，颧骨突出，法令纹深刻，脸型瘦削，肩膀因长期负重而微驼；身穿褪色且沾满油污的蓝色工装外套，内搭破损的灰色背心，裤脚卷起沾满泥土，衣衫褴褛；他正站在光鲜亮丽的橱窗前深吸一口气，神情决绝而满怀期待，准备推门而入，与周围繁华形成强烈反差；背景是明亮的商店橱窗，玻璃反射出繁华街道景象，外部光线呈现冷白色调，内部透出暖金色光芒，冷暖对比强烈；色调冷暖交织，光影层次丰富，构图聚焦人物面部与橱窗倒影的冲突感，氛围充满决绝与希望；电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_5_1776616522.png', 'completed', NULL, '拉杰什深吸一口气，胸口微微起伏，眼神从犹豫转为坚定，衣角被微风轻轻吹动；背景橱窗内的暖金光晕随呼吸节奏产生细微的明暗呼吸感，玻璃反射的街景人流缓慢掠过；镜头缓慢推进至面部特写，捕捉推门瞬间的决绝神态；电影质感，冷暖光影交织，充满无声的誓言与希望。', 'data\\uploads\\shot_5_video_1776626070.mp4', 'completed', 'a06e6d9e-26af-4319-8ee4-454f5be26e98', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:14:30');
INSERT INTO `shots` VALUES (6, 1, 6, '铁盒里的奇迹', '15-18s', '特写', '人物: 拉杰什的手倾倒铁盒，硬币和皱币散落一地，店员惊愕的表情倒影在柜台上；环境: 光滑的大理石柜台，散落的钱币在灯光下闪烁，周围顾客侧目；事件: 倾尽所有购买钢琴；', '高光过曝，聚焦钱币', '震撼、感动', NULL, NULL, '特写镜头，画面主体为拉杰什粗糙古铜色的大手，正倾斜一个旧铁盒，他身穿褪色且沾满油污的蓝色工装外套，袖口磨破，脸上带着新鲜的汗渍和灰尘，神情疲惫却坚毅；动作是倾倒数不清的硬币和皱巴巴的纸币，光滑的大理石柜台上散落着钱币，在强光下闪烁，柜台表面清晰倒映出店员惊愕的表情，周围隐约可见侧目的顾客；环境位于室内商店，高光过曝聚焦于散落的钱币，光线强烈刺眼；美学风格为高对比度色调，戏剧性光影，中心构图，震撼且感动的氛围；电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_6_1776616639.png', 'completed', NULL, '拉杰什粗糙的大手倾斜旧铁盒，硬币与皱币如瀑布般倾泻散落在大理石柜台。强光下钱币剧烈闪烁，柜台倒影中店员惊愕神情微动，周围顾客视线聚焦。镜头极慢推进锁定散落瞬间，高对比度戏剧光影，震撼感人电影质感。', 'data\\uploads\\shot_6_video_1776626117.mp4', 'completed', '953e49d7-a8bc-4c0a-9a00-6b655a92e090', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:15:17');
INSERT INTO `shots` VALUES (7, 1, 7, '铁盒里的奇迹', '18-21s', '全景', '人物: 几个工人合力抬着巨大的白色钢琴箱，拉杰什在一旁护着，脸上洋溢着前所未有的笑容；环境: 狭窄脏乱的小巷，洁白的钢琴箱如同圣物般穿过泥泞；事件: 钢琴运回家；', '画面中心明亮，四周略暗', '喜悦、神圣', NULL, NULL, '全景镜头，画面主体为 45 岁印度男性拉杰什，古铜色粗糙皮肤带有明显日晒痕迹，深黑色瞳孔，眼窝深陷，眼神坚毅且充满慈爱，花白相间略显凌乱的粗硬短发，高鼻梁，颧骨突出，法令纹深刻，瘦削脸型，身高约 170cm，肩膀因长期负重而微驼；他脸上洋溢着前所未有的喜悦笑容；周围有几个工人合力抬着钢琴；环境位于狭窄脏乱的孟买小巷，地面泥泞，洁白的钢琴箱如同圣物般穿过污浊，画面中心明亮四周略暗；色调对比强烈，光影聚焦中心，构图饱满，氛围喜悦而神圣；电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_7_1776627251.png', 'completed', NULL, '工人们抬着白色钢琴箱在泥泞中缓慢前行，拉杰什伴随步伐轻微晃动身体并守护在侧，他的笑容逐渐绽放，巷弄中的灰尘在光束中飞舞。镜头缓慢向前推进，聚焦于拉杰什幸福的面部表情与圣洁的钢琴箱。', 'data\\uploads\\shot_7_video_1776627449.mp4', 'completed', '4c636c3a-937a-4256-93c7-820500c89d4c', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:37:29');
INSERT INTO `shots` VALUES (8, 1, 8, '铁盒里的奇迹', '21-24s', '中近景', '人物: 普里娅揭开琴布，双手捂嘴，眼泪夺眶而出；拉杰什站在身后，手足无措地搓着衣角；环境: 简陋的房间因白色钢琴而变得神圣，阳光透过破窗洒在琴键上；事件: 女儿见到礼物的瞬间；', '柔光滤镜，金色调', '惊喜、温情', NULL, NULL, '中近景镜头，画面主体为 7 岁印度裔女孩普里娅，肤色较白，明亮的大眼睛噙满泪水，扎着两条细长的辫子，身形瘦小，双手紧紧捂住嘴巴，表情充满极度的惊喜与感动；身后站着 45 岁印度男性拉杰什，古铜色粗糙皮肤带有明显日晒痕迹，深陷眼窝中眼神坚毅且充满慈爱，花白相间的凌乱短发，高鼻梁，颧骨突出，法令纹深刻，脸型瘦削，肩膀微驼，身穿褪色且沾满油污的蓝色工装外套内搭破损灰色背心，正手足无措地搓着衣角。环境位于一间简陋的房间，中央摆放着一架神圣的白色钢琴，阳光透过破旧的窗户洒在琴键上形成丁达尔效应，空气中漂浮着微尘。美学风格采用柔光滤镜，金色调主色，温暖光影，中心构图，充满惊喜与温情的氛围。电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_8_1776616695.png', 'completed', NULL, '普里娅双手缓缓捂嘴，泪水夺眶而出，拉杰什在身后局促地搓动衣角；阳光穿透破窗在白色琴键上流动，空气中微尘轻舞；镜头缓慢推进聚焦女孩表情，固定机位捕捉温情瞬间；柔光金色调，电影感真实风格。', 'data\\uploads\\shot_8_video_1776626222.mp4', 'completed', '0ecca2b9-8fa6-428b-9298-7e7d0d66ad37', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:17:02');
INSERT INTO `shots` VALUES (9, 1, 9, '铁盒里的奇迹', '24-27s', '特写', '人物: 普里娅纤细洁白的手指按下琴键，与拉杰什粗糙黝黑的手形成同框对比；环境: 黑白琴键特写，光影交错；事件: 第一次弹奏', '纯净黑白加局部暖色', '纯净、美好', NULL, NULL, '特写镜头，画面主体为两只交叠在钢琴键上的手：左侧是 7 岁印度裔女孩普里娅纤细洁白的手指，皮肤白皙光滑，正轻轻按下琴键；右侧是 45 岁印度裔男性拉杰什粗糙黝黑的大手，古铜色皮肤质感粗砺，布满厚茧和多道陈旧疤痕，指关节粗大变形，与女孩的手形成强烈视觉对比。动作定格在第一次弹奏的瞬间，传递出纯净、美好且充满希望的情绪。环境聚焦于黑白琴键的特写，光影在琴键上交错跳跃。美学风格采用纯净黑白基调辅以局部暖色高光，强调质感对比与细腻的光影层次，构图紧凑聚焦。电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_9_1776616704.png', 'completed', NULL, '女孩纤细的手指轻盈按下琴键，父亲粗糙的大手在旁微微颤抖给予支撑；黑白琴键上光影随动作流动流转，局部暖色高光温柔闪烁；镜头极慢推近聚焦指尖触碰的瞬间，定格纯净美好的希望氛围。', 'data\\uploads\\shot_9_video_1776626393.mp4', 'completed', '3a8af040-f843-4572-9d51-6b7e86994072', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:19:53');
INSERT INTO `shots` VALUES (10, 1, 10, '铁盒里的奇迹', '27-30s', '远景拉升', '人物: 父女俩在屋顶弹琴，周围是密集的贫民窟，但音乐声仿佛覆盖了整个区域；环境: 黄昏的孟买天际线，夕阳将云层染成紫红色；事件: 音乐飘扬；', '绚丽的晚霞紫红与金黄', '升华、宏大', NULL, NULL, '远景拉升镜头，画面主体为 45 岁印度裔男性拉杰什与 7 岁印度裔小女孩普里娅；拉杰什拥有古铜色粗糙皮肤且带有明显日晒痕迹，深黑色瞳孔深陷，眼神坚毅慈爱，花白相间凌乱短发，高鼻梁颧骨突出，法令纹深刻，脸型瘦削，体型精瘦肌肉结实，肩膀微驼，双手布满厚茧、陈旧疤痕且指关节粗大变形，身穿褪色沾满油污的蓝色工装外套，内搭破损灰色背心，裤脚卷起沾满泥土；普里娅肤色较白，拥有明亮大眼睛，扎着两条细长辫子，身形瘦小；两人坐在屋顶上共同弹奏乐器，神情专注而宁静，流露出超越苦难的幸福与升华感；背景是黄昏时分密集的孟买贫民窟建筑群，夕阳将天际线的云层染成绚丽的紫红色与金黄色，音乐仿佛具象化地飘扬在空气中；色调采用紫红与金黄的强烈对比，光影呈现戏剧性的逆光轮廓光，构图宏大开阔，氛围神圣而充满希望；电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_10_1776616712.png', 'completed', NULL, '拉杰什与普里娅在屋顶专注弹琴，背景是黄昏下紫红金黄交织的孟买贫民窟天际线；父女手指在琴弦上灵动跳跃，发丝与衣角随晚风轻微飘动，云层在夕阳中缓慢流转；镜头从人物特写缓缓拉升展现宏大全景；画面充满神圣希望的电影感氛围。', 'data\\uploads\\shot_10_video_1776626451.mp4', 'completed', 'd965bdc2-012f-429e-9ebb-4ed03183a26e', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:20:51');
INSERT INTO `shots` VALUES (11, 1, 11, '无声的共鸣', '30-33s', '特写', '人物: 拉杰什闭着眼聆听，眼角滑落一滴泪水，划过满是皱纹的脸颊；环境: 虚化的背景，焦点全在父亲感动的脸上；事件: 父亲流泪；', '暖色调，柔焦', '释放、幸福', NULL, NULL, '特写镜头，45 岁印度裔男性拉杰什，古铜色粗糙皮肤带有明显日晒痕迹，深黑色瞳孔紧闭，眼窝深陷，花白相间且略显凌乱的粗硬短发，高鼻梁，颧骨突出，法令纹深刻，瘦削脸型，体型精瘦肌肉结实；身穿褪色且沾满油污的蓝色工装外套，内搭破损灰色背心；双眼紧闭正在深情聆听，眼角滑落一滴晶莹泪水划过满是皱纹的脸颊，神情中流露出极致的释放与幸福，充满慈爱；背景完全虚化，焦点牢牢锁定在父亲感动的面部细节上；暖色调，柔焦效果，细腻光影，情感饱满构图，温馨感人氛围；电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_11_1776617053.png', 'completed', NULL, '拉杰什紧闭的双眼微微颤动，一滴晶莹泪水顺着粗糙脸颊缓缓滑落，花白头发在微风中轻拂；背景保持柔焦虚化，光影随情绪流动更显温暖；镜头极缓慢推进聚焦泪痕，固定机位捕捉细微表情；暖色调柔焦风格，释放与幸福的感人氛围。', 'data\\uploads\\shot_11_video_1776626498.mp4', 'completed', '919294cc-30f8-4cfd-af20-63087f17a86d', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:21:38');
INSERT INTO `shots` VALUES (12, 1, 12, '无声的共鸣', '33-36s', '分屏对比', '人物: 左边是拉杰什满是伤痕的手搬铁块，右边是普里娅优雅弹琴的手；环境: 左暗右明，视觉冲击强烈；事件: 因果展示', '左灰暗右明亮', '对比、震撼', NULL, NULL, '分屏对比构图，左侧画面主体为 45 岁印度裔男性拉杰什的双手特写，古铜色粗糙皮肤布满厚茧与多道陈旧疤痕，指关节粗大变形，正用力搬动沉重铁块，动作紧绷充满力量感；右侧画面主体为 7 岁印度裔女孩普里娅的双手特写，肤色较白细腻，手指纤细修长，正优雅地按压钢琴琴键，动作轻柔灵动。环境上左侧背景昏暗压抑，笼罩在工厂阴影中，右侧背景明亮温暖，洒满柔和的自然光。色调呈现左灰暗右明亮的强烈反差，光影戏剧化，构图对称且极具视觉冲击力，氛围震撼人心，传达命运因果的无声共鸣。电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_12_1776616757.png', 'completed', NULL, '左侧粗糙双手用力搬起铁块，右侧纤细手指轻柔按压琴键；左暗右明光影随动作微调；镜头固定强化分屏对比；电影感写实风格。', 'data\\uploads\\shot_12_video_1776626545.mp4', 'completed', '2f4ecf86-8eb8-4383-a19e-47512389c0e8', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:22:25');
INSERT INTO `shots` VALUES (13, 1, 13, '无声的共鸣', '36-39s', '中景', '人物: 普里娅转头看向父亲，露出灿烂笑容，拉杰什竖起大拇指；环境: 温馨的室内光，尘埃在光束中跳舞；事件: 父女互动；', '温馨橙黄', '和谐、圆满', NULL, NULL, '中景镜头，画面主体为 7 岁印度裔女孩普里娅与 45 岁印度裔父亲拉杰什；普里娅肤色较白，拥有明亮的大眼睛，扎着两条细长的辫子，身形瘦小，正转头看向父亲，脸上露出灿烂纯真的笑容；拉杰什拥有古铜色粗糙皮肤，带有明显日晒痕迹，深黑色瞳孔，眼窝深陷，眼神坚毅且充满慈爱，花白相间的短发略显凌乱，高鼻梁，颧骨突出，法令纹深刻，脸型瘦削，体型精瘦但肌肉结实，肩膀微驼，双手布满厚茧和多道陈旧疤痕，指关节粗大变形，身穿褪色且沾满油污的蓝色工装外套，内穿破损的灰色背心，裤脚卷起沾满泥土，此刻正对着女儿竖起大拇指，神情中流露出无声的骄傲与爱意；环境为温馨的室内场景，温暖的橙黄色光束穿过窗户洒入，空气中尘埃在光束中飞舞，营造出静谧而神圣的时刻；色调温馨橙黄，光影柔和且具有体积感，构图紧凑聚焦于父女间的情感交流，氛围和谐圆满；电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_13_1776616762.png', 'completed', NULL, '普里娅转头看向父亲并绽放灿烂笑容，拉杰什缓缓竖起大拇指，光束中尘埃轻盈飞舞；镜头缓慢推进聚焦父女眼神交流；温馨橙黄光影，电影感真实风格。', 'data\\uploads\\shot_13_video_1776626591.mp4', 'completed', 'ee6a8d10-c3d9-40ab-9c6a-e5887417ddb4', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:23:11');
INSERT INTO `shots` VALUES (14, 1, 14, '无声的共鸣', '39-42s', '特写', '人物: 空了的铁盒子被放在钢琴顶上，里面放着一朵小花；环境: 钢琴漆面反射出花朵的倒影；事件: 象征物定格；', '柔和自然光', '余韵悠长', NULL, NULL, '特写镜头，画面主体为一个陈旧的铁皮盒子放置在黑色钢琴光滑的漆面上，盒内空空如也，仅中央摆放着一朵娇嫩的小黄花；环境描写为柔和的自然光洒落，钢琴深邃的黑色漆面清晰反射出花朵与铁盒的倒影，光影交错间尘埃微舞；美学短词：暖色调，柔焦，极简构图，静谧氛围，余韵悠长；电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_14_1776616826.png', 'completed', NULL, '铁盒与小花静置钢琴漆面，柔和自然光下倒影清晰；微尘在光束中缓缓浮动，花瓣随风极轻微颤动；镜头固定特写，营造静谧悠长的电影氛围。', 'data\\uploads\\shot_14_video_1776626638.mp4', 'completed', '82775820-043d-44cb-b513-72484363245b', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:23:58');
INSERT INTO `shots` VALUES (15, 1, 15, '无声的共鸣', '42-45s', '大远景', '人物: 无具体人物，只有城市灯火和一轮明月；环境: 璀璨的城市夜景，星光点点；事件: 画面渐黑', '深蓝夜色配暖黄灯火', '宁静、深远', NULL, NULL, '大远景镜头，画面中无具体人物，主体为孟买城市璀璨的夜景与一轮高悬的明月；环境描绘为深邃的夜空下，密集的城市建筑群灯火通明，无数暖黄色的窗户灯光如繁星般点缀在街道与高楼之间，星光点点，画面边缘呈现渐黑效果；色调采用深蓝夜色搭配温暖昏黄的灯火，光影对比柔和而富有层次，构图宏大开阔，营造出宁静、深远且充满敬意的氛围；电影感，真实照片风格，8K 高清，竖屏 9:16', 'data\\uploads\\shot_15_1776617130.png', 'completed', NULL, '城市灯火在夜色中微微闪烁，月光洒下柔和的光晕；镜头缓慢拉远并伴随轻微上升运动，画面边缘逐渐融入黑暗；深蓝与暖黄交织，营造宁静深远的电影氛围。', 'data\\uploads\\shot_15_video_1776626684.mp4', 'completed', 'd0c4fef3-7dc5-4cd3-9284-40cf5026d3d4', 3, NULL, NULL, '2026-04-19 10:27:43', '2026-04-19 19:24:44');
INSERT INTO `shots` VALUES (16, 2, 1, '雨夜屈辱', '0-3s', '远景 (Long Shot)', '人物: 微小的米娜身影孤零零站在雨中；环境: 暴雨倾盆，霓虹灯倒影在积水路面，冷色调，压抑氛围；事件: 大雨冲刷着街道，米娜在橱窗前显得渺小无助', '冷灰蓝，高对比度', '孤独，寒冷', NULL, NULL, '远景，雨夜的伦敦街头，一个 8 岁南亚女孩米娜独自站在奢侈品店橱窗前，全身湿透，冷灰蓝色调，霓虹灯反射在积水路面，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', 'data\\uploads\\shot_16_1776796766.png', 'completed', NULL, '大雨倾盆而下，路面积水泛起涟漪，女孩在风中微微颤抖，镜头缓慢推进', 'data\\uploads\\shot_16_video_1776796859.mp4', 'completed', 'e7810876-40fa-410d-b375-1482a542797d', 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:40:59');
INSERT INTO `shots` VALUES (17, 2, 2, '雨夜屈辱', '3-6s', '中景 (Medium Shot)', '人物: 白人男子愤怒指责，米娜畏缩后退；环境: 明亮的橱窗内展示着金色舞裙，与外部黑暗形成强烈对比；事件: 男子手指指着米娜额头驱赶，米娜害怕地后退', '冷暖对比强烈', '冲突，压迫', NULL, NULL, '中景，衣着光鲜的白人男子愤怒地指着 8 岁南亚女孩米娜，女孩畏缩后退，身后橱窗内金色舞裙闪耀，冷暖光对比，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', 'data\\uploads\\shot_17_1776796775.png', 'completed', NULL, '男子手指向前伸出，女孩身体后仰，雨水顺着脸颊滑落，镜头轻微晃动表现紧张感', 'data\\uploads\\shot_17_video_1776796908.mp4', 'completed', '479090f3-e1f5-45a2-8d25-c934fae612ea', 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:41:48');
INSERT INTO `shots` VALUES (18, 2, 3, '雨夜屈辱', '6-9s', '特写 (Close-up)', '人物: 米娜泪流满面，眼神绝望；环境: 背景虚化，只有雨水和模糊的灯光；事件: 泪水混合雨水从米娜眼中涌出，嘴唇颤抖', '暗蓝色，柔焦', '悲伤，心碎', NULL, NULL, '特写，8 岁南亚女孩米娜的脸部，泪水混合雨水滑落，眼神充满绝望和无助，背景虚化，暗蓝色调，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', 'data\\uploads\\shot_18_1776796783.png', 'completed', NULL, '眼泪大颗滚落，女孩眨眼，雨水打在睫毛上，微距镜头捕捉表情细节', 'data\\uploads\\shot_18_video_1776796957.mp4', 'completed', 'edeced95-66b7-4576-a58b-bf68449c7fd6', 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:37');
INSERT INTO `shots` VALUES (19, 2, 4, '雨夜屈辱', '9-12s', '中近景 (Medium Close-up)', '人物: 母亲萨维特里撑伞出现，拥抱米娜；环境: 一把破旧黑伞遮住两人，周围依然是冷雨；事件: 母亲焦急跑来，将米娜紧紧抱在怀里安慰', '略微转暖的灰色', '温情，依靠', NULL, NULL, '中近景，35 岁南亚母亲萨维特里撑着破伞抱住哭泣的女儿米娜，母亲神情焦虑又慈爱，雨夜街头，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '母亲快速入画，张开双臂拥抱，雨伞在风中倾斜，镜头跟随动作移动', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:37');
INSERT INTO `shots` VALUES (20, 2, 5, '雨夜屈辱', '12-15s', '特写 (Close-up)', '人物: 萨维特里看着橱窗内的金裙，眼神变得坚定；环境: 瞳孔中倒映着金色舞裙的光芒；事件: 母亲咬紧牙关，眼神从心疼转为决绝', '眼中有一点金光', '决心，誓言', NULL, NULL, '特写，35 岁南亚母亲萨维特里的眼睛，瞳孔中倒映着金色舞裙的光芒，眼神从悲伤转为坚定，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '眼球微微转动，瞳孔中的金光闪烁，睫毛颤动，表现内心活动', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:37');
INSERT INTO `shots` VALUES (21, 2, 6, '血汗筑梦', '15-18s', '全景 (Full Shot)', '人物: 米娜抱着泰迪熊睡在地板上，母亲在角落数零钱；环境: 墙壁斑驳，只有一盏昏黄灯泡，气氛清贫；事件: 母亲在微光下仔细整理皱巴巴的硬币和纸币', '昏黄，低饱和度', '艰辛，期盼', NULL, NULL, '全景，简陋出租屋内，8 岁女孩米娜睡在地板垫子上，35 岁母亲萨维特里在角落昏黄灯光下数零钱，墙壁斑驳，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '母亲手指轻轻捻过纸币，灯光摇曳，女孩呼吸起伏，固定镜头', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:37');
INSERT INTO `shots` VALUES (22, 2, 7, '血汗筑梦', '18-21s', '中景 (Medium Shot)', '人物: 萨维特里在油锅前忙碌，满脸油烟；环境: 烟雾缭绕，火光映照，环境嘈杂脏乱；事件: 母亲被热油溅到手，皱眉忍耐，继续翻炒食物', '橙红与黑灰交织', '煎熬，坚持', NULL, NULL, '中景，35 岁南亚母亲萨维特里在街头小吃摊炸食物，脸上沾满油烟，被热油溅到后忍痛继续工作，火光映照，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '油锅沸腾冒烟，母亲手部动作迅速，火焰升腾，镜头轻微推近', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:37');
INSERT INTO `shots` VALUES (23, 2, 8, '血汗筑梦', '21-24s', '低角度仰拍 (Low Angle)', '人物: 萨维特里头顶重砖筐，步履蹒跚；环境: 尘土飞扬，钢筋水泥林立，阳光刺眼；事件: 母亲扛着沉重的红砖，汗水如雨下，双腿颤抖', '土黄色，高对比度', '沉重，负荷', NULL, NULL, '低角度仰拍，35 岁南亚母亲萨维特里头顶装满红砖的筐，在建筑工地艰难行走，尘土飞扬，汗水直流，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '母亲脚步沉重踏起灰尘，身体因负重而摇晃，镜头跟随脚步移动', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:37');
INSERT INTO `shots` VALUES (24, 2, 9, '血汗筑梦', '24-27s', '特写 (Close-up)', '人物: 萨维特里红肿溃烂的双手在污水中洗碗；环境: 冰冷的水，堆积如山的脏盘子，阴暗潮湿；事件: 双手用力搓洗盘子，伤口接触冷水产生刺痛感', '青灰色，冷光', '痛苦，牺牲', NULL, NULL, '特写，35 岁南亚母亲萨维特里红肿溃烂的双手在冰冷污水中清洗脏盘子，伤口清晰可见，青灰色调，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '水流冲刷双手，手指因疼痛而蜷缩又伸直，泡沫破裂，微距镜头', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:37');
INSERT INTO `shots` VALUES (25, 2, 10, '血汗筑梦', '27-30s', '蒙太奇快切 (Montage)', '人物: 母亲在不同场景中疲惫的身影；环境: 快速切换的工地、厨房、街头；事件: 时间流逝，母亲的白发增多，背更驼，但手中的钱变多', '节奏明快，色彩随场景变化', '紧迫，积累', NULL, NULL, '蒙太奇画面，35 岁南亚母亲萨维特里在工地、厨房、街头劳作的快速剪辑，表情日益疲惫但眼神坚定，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '画面快速闪回，动作连贯，配合时钟转动特效，表现时间流逝', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:37');
INSERT INTO `shots` VALUES (26, 2, 11, '血汗筑梦', '30-33s', '特写 (Close-up)', '人物: 一叠厚厚的零钱；环境: 粗糙的手掌上托着来之不易的积蓄；事件: 母亲将最后一枚硬币放入，握紧拳头', '暖金色光晕', '希望，达成', NULL, NULL, '特写，35 岁南亚母亲萨维特里粗糙的手掌托着一叠皱巴巴的零钱，暖金色光晕笼罩，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '手指轻轻合拢握住钱币，光线在指缝间闪烁，镜头缓慢拉远', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:37');
INSERT INTO `shots` VALUES (27, 2, 12, '血汗筑梦', '33-36s', '中景 (Medium Shot)', '人物: 萨维特里整理衣角，深吸一口气走进去；环境: 阳光明媚，店铺玻璃干净明亮；事件: 母亲鼓起勇气，推开那扇曾经让她自卑的门', '明亮自然光', '勇敢，转折', NULL, NULL, '中景，35 岁南亚母亲萨维特里穿着整洁的纱丽，在白天阳光下深吸一口气，推开舞裙店的玻璃门，明亮自然光，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '门被推开，风铃作响，母亲迈步进入，镜头跟随背影', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:37');
INSERT INTO `shots` VALUES (28, 2, 13, '血汗筑梦', '36-40s', '中近景 (Medium Close-up)', '人物: 萨维特里递出钱，店员递出金裙；环境: 店内豪华，金色舞裙在灯光下熠熠生辉；事件: 交易完成，母亲双手接过金裙，脸上露出难以置信的喜悦', '璀璨金黄', '狂喜，释放', NULL, NULL, '中近景，35 岁南亚母亲萨维特里双手接过华丽的金色舞裙，脸上绽放出灿烂喜悦的笑容，店内灯光璀璨，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '母亲笑容展开，眼中含泪，金裙在手中抖动发出光芒，镜头环绕', NULL, 'failed', NULL, 4, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:37');
INSERT INTO `shots` VALUES (29, 2, 14, '金色涅槃', '40-43s', '中景 (Medium Shot)', '人物: 米娜打开礼物，惊喜尖叫；环境: 破旧房间被金裙的光芒照亮；事件: 米娜穿上金裙，在狭小空间里快乐旋转', '温馨暖黄', '纯真，幸福', NULL, NULL, '中景，8 岁南亚女孩米娜在破旧家中打开礼物，穿上金色舞裙快乐旋转，房间被金光照亮，温馨暖黄调，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '女孩原地旋转，裙摆飞扬，脸上洋溢着纯粹的快乐，镜头跟随旋转', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:37');
INSERT INTO `shots` VALUES (30, 2, 15, '金色涅槃', '43-46s', '大远景 (Extreme Long Shot)', '人物: 舞台上渺小的身影逐渐变大；环境: 宏大的剧院，座无虚席，聚光灯汇聚；事件: 幕布拉开，灯光聚焦', '深蓝背景，金色光束', '宏大，期待', NULL, NULL, '大远景，宏大的伦敦舞蹈节剧院舞台，聚光灯汇聚在中央，观众席黑暗中人头攒动，深蓝背景金色光束，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '幕布缓缓拉开，聚光灯亮起，镜头从高空俯冲向下', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:38');
INSERT INTO `shots` VALUES (31, 2, 16, '金色涅槃', '46-49s', '全景 (Full Shot)', '人物: 米娜身着金裙，自信起舞；环境: 绚丽的舞台灯光，梦幻的背景；事件: 米娜做出高难度舞蹈动作，脚铃清脆作响', '绚丽紫蓝与金黄', '震撼，华丽', NULL, NULL, '全景，8 岁南亚女孩米娜身着华丽金色舞裙在舞台中央自信起舞，动作优美，脚铃闪烁，绚丽紫蓝与金黄色调，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '女孩高高跃起旋转，裙摆如花绽放，光效粒子飞舞，慢动作镜头', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:38');
INSERT INTO `shots` VALUES (32, 2, 17, '金色涅槃', '49-52s', '特写 (Close-up)', '人物: 米娜自信微笑，汗水闪光；环境: 背景是模糊的观众和灯光；事件: 米娜眼神坚定，展现出与雨夜截然不同的自信', '高光，柔焦', '自信，荣耀', NULL, NULL, '特写，8 岁南亚女孩米娜在舞台上的面部特写，自信灿烂的微笑，汗水在灯光下闪光，眼神坚定，高光柔焦，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '女孩转头面向观众，笑容绽放，头发随风飘动，镜头缓慢推近', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:38');
INSERT INTO `shots` VALUES (33, 2, 18, '金色涅槃', '52-55s', '中景 (Medium Shot)', '人物: 米娜献花给母亲萨维特里；环境: 舞台边缘，母亲身穿粉色纱丽起身；事件: 米娜跑向母亲，献上鲜花，两人紧紧相拥', '温暖粉红', '感恩，深情', NULL, NULL, '中景，8 岁女孩米娜在舞台边缘将鲜花献给身穿粉色纱丽的母亲萨维特里，两人紧紧相拥，温暖粉色调，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '女孩奔跑，递花，母亲弯腰拥抱，花瓣飘落，镜头横向跟随', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:38');
INSERT INTO `shots` VALUES (34, 2, 19, '金色涅槃', '55-58s', '特写 (Close-up)', '人物: 母女二人泪光闪烁，笑容温暖；环境: 背景虚化成光斑；事件: 母女目光交汇，无需言语的默契与感动', '极致暖光', '圆满，感动', NULL, NULL, '特写，8 岁女孩米娜和 35 岁母亲萨维特里对视，眼中含泪面带微笑，背景虚化成光斑，极致暖光，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '两人眼神交流，泪水在眼眶打转，嘴角上扬，镜头静止聚焦情感', NULL, 'failed', NULL, 3, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:38');
INSERT INTO `shots` VALUES (35, 2, 20, '金色涅槃', '58-60s', '远景 (Long Shot)', '人物: 母女牵手向观众致意；环境: 全场掌声，彩带飘落，灯光辉煌；事件: 画面定格在母女牵手的剪影，字幕浮现', '辉煌多彩', '升华，希望', NULL, NULL, '远景，舞台全景，8 岁女孩米娜和 35 岁母亲萨维特里牵手向观众致意，彩带飘落，灯光辉煌，辉煌多彩色调，日式动漫风格，赛璐璐着色，精致线条，鲜艳色彩，竖屏 9:16', NULL, 'failed', NULL, '彩带漫天飞舞，灯光闪烁，镜头缓缓拉远直至黑屏，结束', NULL, 'failed', NULL, 2, NULL, NULL, '2026-04-21 18:39:01', '2026-04-21 18:42:38');

-- ----------------------------
-- Table structure for social_accounts
-- ----------------------------
DROP TABLE IF EXISTS `social_accounts`;
CREATE TABLE `social_accounts`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `platform` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `account_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `account_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `auth_data` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `is_active` tinyint(1) NOT NULL,
  `last_publish_at` datetime(0) NULL DEFAULT NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `user_id`(`user_id`) USING BTREE,
  CONSTRAINT `social_accounts_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of social_accounts
-- ----------------------------

-- ----------------------------
-- Table structure for storyboards
-- ----------------------------
DROP TABLE IF EXISTS `storyboards`;
CREATE TABLE `storyboards`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `script_id` int(11) NOT NULL,
  `total_shots` int(11) NOT NULL,
  `total_duration` int(11) NULL DEFAULT NULL,
  `tone_mapping` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `script_id`(`script_id`) USING BTREE,
  CONSTRAINT `storyboards_ibfk_1` FOREIGN KEY (`script_id`) REFERENCES `scripts` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of storyboards
-- ----------------------------
INSERT INTO `storyboards` VALUES (1, 2, 15, 45, NULL, '2026-04-19 10:27:43', '2026-04-19 10:27:43');
INSERT INTO `storyboards` VALUES (2, 3, 20, 60, NULL, '2026-04-21 18:39:01', '2026-04-21 18:39:01');

-- ----------------------------
-- Table structure for user_quotas
-- ----------------------------
DROP TABLE IF EXISTS `user_quotas`;
CREATE TABLE `user_quotas`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `quota_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `used_count` int(11) NOT NULL,
  `limit_count` int(11) NOT NULL,
  `period` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `reset_at` datetime(0) NULL DEFAULT NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `user_id`(`user_id`) USING BTREE,
  CONSTRAINT `user_quotas_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of user_quotas
-- ----------------------------
INSERT INTO `user_quotas` VALUES (1, 1, 'image_generation', 0, 100, 'monthly', NULL, '2026-04-18 18:10:36', '2026-04-18 18:10:36');
INSERT INTO `user_quotas` VALUES (2, 1, 'video_generation', 0, 100, 'monthly', NULL, '2026-04-18 18:10:36', '2026-04-18 18:10:36');
INSERT INTO `user_quotas` VALUES (3, 1, 'script_generation', 0, 100, 'monthly', NULL, '2026-04-18 18:10:36', '2026-04-18 18:10:36');
INSERT INTO `user_quotas` VALUES (4, 1, 'publish', 0, 100, 'monthly', NULL, '2026-04-18 18:10:36', '2026-04-18 18:10:36');
INSERT INTO `user_quotas` VALUES (5, 2, 'image_generation', 0, 100, 'monthly', NULL, '2026-04-18 18:16:19', '2026-04-18 18:16:19');
INSERT INTO `user_quotas` VALUES (6, 2, 'video_generation', 0, 100, 'monthly', NULL, '2026-04-18 18:16:19', '2026-04-18 18:16:19');
INSERT INTO `user_quotas` VALUES (7, 2, 'script_generation', 0, 100, 'monthly', NULL, '2026-04-18 18:16:19', '2026-04-18 18:16:19');
INSERT INTO `user_quotas` VALUES (8, 2, 'publish', 0, 100, 'monthly', NULL, '2026-04-18 18:16:19', '2026-04-18 18:16:19');
INSERT INTO `user_quotas` VALUES (9, 3, 'image_generation', 0, 100, 'monthly', NULL, '2026-04-21 16:41:33', '2026-04-21 16:41:33');
INSERT INTO `user_quotas` VALUES (10, 3, 'video_generation', 0, 100, 'monthly', NULL, '2026-04-21 16:41:33', '2026-04-21 16:41:33');
INSERT INTO `user_quotas` VALUES (11, 3, 'script_generation', 0, 100, 'monthly', NULL, '2026-04-21 16:41:33', '2026-04-21 16:41:33');
INSERT INTO `user_quotas` VALUES (12, 3, 'publish', 0, 100, 'monthly', NULL, '2026-04-21 16:41:33', '2026-04-21 16:41:33');

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `hashed_password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `display_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `avatar_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `role` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  `updated_at` datetime(0) NOT NULL DEFAULT CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `email`(`email`) USING BTREE,
  UNIQUE INDEX `username`(`username`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of users
-- ----------------------------
INSERT INTO `users` VALUES (1, 'admin', 'admin@example.com', '$pbkdf2-sha256$120000$DoFQKiWEEGIMQci5l3LOGQ$1fla3/C.R0eC64WNYFbzVuv0HkgyWaghNKuimabkSUQ', NULL, NULL, 'user', 1, '2026-04-18 18:10:36', '2026-04-18 18:10:36');
INSERT INTO `users` VALUES (2, 'tester', 'tester@example.com', '$pbkdf2-sha256$120000$BoCwFgJgzNl7z7m3lpIyZg$7f.QcVzJkPwaifNqhSAc9xD3DlCpbhQ6FZS.zYf2KnA', NULL, NULL, 'user', 1, '2026-04-18 18:16:19', '2026-04-18 18:16:19');
INSERT INTO `users` VALUES (3, 'tester1', 'lucas901206@gmail.com', '$pbkdf2-sha256$120000$qpXSGiOklJIy5lzrfS.FcA$18fshjyKXenBfNXXA/T2RVsKX/7QA0ZKaLRlck9DC5U', NULL, NULL, 'user', 1, '2026-04-21 16:41:33', '2026-04-21 16:41:33');

-- ----------------------------
-- Table structure for workflow_steps
-- ----------------------------
DROP TABLE IF EXISTS `workflow_steps`;
CREATE TABLE `workflow_steps`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `project_id` int(11) NOT NULL,
  `step_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `step_order` int(11) NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `celery_task_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `progress` int(11) NOT NULL,
  `error_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `started_at` datetime(0) NULL DEFAULT NULL,
  `completed_at` datetime(0) NULL DEFAULT NULL,
  `created_at` datetime(0) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `project_id`(`project_id`) USING BTREE,
  CONSTRAINT `workflow_steps_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of workflow_steps
-- ----------------------------
INSERT INTO `workflow_steps` VALUES (1, 1, 'generate_image_prompts', 0, 'completed', NULL, 100, NULL, '2026-04-19 12:41:38', '2026-04-19 12:48:35', '2026-04-19 12:41:38');
INSERT INTO `workflow_steps` VALUES (2, 1, 'generate_images', 0, 'completed', 'b3435219-3d15-4d29-a59e-1b2e7b123581', 100, NULL, '2026-04-19 14:43:17', '2026-04-19 14:43:48', NULL);
INSERT INTO `workflow_steps` VALUES (3, 1, 'generate_images', 0, 'completed', '7bbe2b01-71b6-409d-af7a-30adff202ad3', 100, NULL, '2026-04-19 15:23:27', '2026-04-19 15:24:33', NULL);
INSERT INTO `workflow_steps` VALUES (4, 1, 'generate_images', 0, 'completed', 'e8035a2c-1b2a-4891-b09f-e6a6fe37b9af', 100, NULL, '2026-04-19 16:15:12', '2026-04-19 16:16:05', NULL);
INSERT INTO `workflow_steps` VALUES (5, 1, 'generate_images', 0, 'completed', '467b69a9-ae3d-42b1-b9e8-133ff0147008', 100, NULL, '2026-04-19 16:17:29', '2026-04-19 16:22:07', NULL);
INSERT INTO `workflow_steps` VALUES (6, 1, 'generate_image_prompts', 0, 'completed', 'a63f1a72-6088-4674-9e6f-32022e578122', 100, NULL, '2026-04-19 16:32:28', '2026-04-19 16:32:58', NULL);
INSERT INTO `workflow_steps` VALUES (7, 1, 'generate_images', 0, 'completed', '1e1e3f52-f6f5-4a37-bad8-a311acedeb5e', 100, NULL, '2026-04-19 16:41:34', '2026-04-19 16:41:41', NULL);
INSERT INTO `workflow_steps` VALUES (8, 1, 'generate_videos', 0, 'failed', 'd73223c3-9171-431c-a8db-851e128c87c6', 0, '\'generate_videos_for_shots\' object has no attribute \'_mark_video_failed\'', '2026-04-19 16:59:44', '2026-04-19 16:59:47', NULL);
INSERT INTO `workflow_steps` VALUES (9, 1, 'generate_videos', 0, 'completed', '657158c1-41bd-4340-9f7e-94f67aa35d66', 100, NULL, '2026-04-19 17:06:03', '2026-04-19 17:06:07', NULL);
INSERT INTO `workflow_steps` VALUES (10, 1, 'generate_videos', 0, 'completed', '8c913892-49a8-4a2b-8924-73cb03c750fc', 100, NULL, '2026-04-19 17:11:15', '2026-04-19 17:11:16', NULL);
INSERT INTO `workflow_steps` VALUES (11, 1, 'generate_videos', 0, 'completed', '40cddca8-4734-409f-8fde-cf55a1d84a5a', 100, NULL, '2026-04-19 17:24:39', '2026-04-19 17:24:41', NULL);
INSERT INTO `workflow_steps` VALUES (12, 1, 'generate_videos', 0, 'completed', '55f08c47-97f1-4b32-b929-93f15b0960ee', 100, NULL, '2026-04-19 18:16:27', '2026-04-19 18:16:30', NULL);
INSERT INTO `workflow_steps` VALUES (13, 1, 'generate_videos', 0, 'completed', '9586b46a-370f-46d8-8748-0f92baab414c', 100, NULL, '2026-04-19 18:36:39', '2026-04-19 18:37:38', NULL);
INSERT INTO `workflow_steps` VALUES (14, 1, 'generate_videos', 0, 'completed', 'e8b41041-aa66-4018-ba9d-67d4e5330aa4', 100, NULL, '2026-04-19 19:07:46', '2026-04-19 19:08:34', NULL);
INSERT INTO `workflow_steps` VALUES (15, 1, 'generate_videos', 0, 'completed', '5fd0d065-82a4-4f84-9175-a0678f80e9e3', 100, NULL, '2026-04-19 19:09:54', '2026-04-19 19:11:28', NULL);
INSERT INTO `workflow_steps` VALUES (16, 1, 'generate_videos', 0, 'completed', 'a034721b-96a4-4ec0-a1d2-261248fd4447', 100, NULL, '2026-04-19 19:12:35', '2026-04-19 19:17:02', NULL);
INSERT INTO `workflow_steps` VALUES (17, 1, 'generate_videos', 0, 'completed', '6ae601f3-6a94-4ca4-a763-790dc81277d4', 100, NULL, '2026-04-19 19:18:56', '2026-04-19 19:24:45', NULL);
INSERT INTO `workflow_steps` VALUES (18, 1, 'generate_videos', 0, 'completed', '1f1fc09d-90d7-4103-b321-3a6ec49d3dad', 100, NULL, '2026-04-19 19:27:15', '2026-04-19 19:28:02', NULL);
INSERT INTO `workflow_steps` VALUES (19, 1, 'generate_images', 0, 'completed', '5373e097-e0d6-4068-b875-2e93aa3c05ba', 100, NULL, '2026-04-19 19:31:19', '2026-04-19 19:31:51', NULL);
INSERT INTO `workflow_steps` VALUES (20, 1, 'generate_videos', 0, 'completed', '822a95d3-4224-432a-bad3-bcf69cf50338', 100, NULL, '2026-04-19 19:35:23', '2026-04-19 19:36:10', NULL);
INSERT INTO `workflow_steps` VALUES (21, 1, 'generate_videos', 0, 'completed', '1b1f177f-44a9-4304-9051-62e83a27fb83', 100, NULL, '2026-04-19 19:36:43', '2026-04-19 19:37:30', NULL);
INSERT INTO `workflow_steps` VALUES (22, 1, 'merge_videos', 0, 'failed', '8d0dac70-4f4d-4dd7-afa8-2dce1f4ac11b', 0, 'merge_project_videos() got an unexpected keyword argument \'shot_ids\'', '2026-04-19 19:48:11', '2026-04-19 19:48:12', NULL);
INSERT INTO `workflow_steps` VALUES (23, 1, 'merge_videos', 0, 'failed', 'cd3c5076-341d-4117-9a35-fdb87cfc7db7', 0, 'merge_project_videos() got an unexpected keyword argument \'shot_ids\'', '2026-04-19 19:51:08', '2026-04-19 19:51:08', NULL);
INSERT INTO `workflow_steps` VALUES (24, 1, 'merge_videos', 0, 'completed', 'd967e9f3-2f69-406a-8398-8f64bbe9288e', 100, NULL, '2026-04-19 19:53:16', '2026-04-19 19:53:53', NULL);
INSERT INTO `workflow_steps` VALUES (25, 1, 'merge_videos', 0, 'completed', '1de1de9b-8317-4667-8154-90477d4b3f06', 100, NULL, '2026-04-19 19:55:39', '2026-04-19 19:56:16', NULL);
INSERT INTO `workflow_steps` VALUES (26, 1, 'generate_character_images', 0, 'running', NULL, 0, NULL, '2026-04-20 01:53:14', NULL, NULL);
INSERT INTO `workflow_steps` VALUES (27, 2, 'auto_generate', 0, 'running', 'cce22fbf-db23-4461-b935-c2048a237fb1', 0, NULL, '2026-04-21 18:20:13', NULL, NULL);
INSERT INTO `workflow_steps` VALUES (28, 2, 'auto_generate', 0, 'running', '4d949ebe-e771-49d8-a5d6-d75e3ece2159', 0, NULL, '2026-04-21 18:23:18', NULL, NULL);
INSERT INTO `workflow_steps` VALUES (29, 2, 'auto_generate', 0, 'failed', '803fb1af-0d07-4588-aecc-3907f3bc8fe6', 0, 'sequence item 0: expected str instance, dict found', '2026-04-21 18:29:17', '2026-04-21 18:29:17', NULL);
INSERT INTO `workflow_steps` VALUES (30, 2, 'auto_generate', 0, 'failed', 'b69dc120-e3df-4a9b-80a7-fd58e23c2bf8', 0, 'sequence item 0: expected str instance, dict found', '2026-04-21 18:33:36', '2026-04-21 18:33:37', NULL);
INSERT INTO `workflow_steps` VALUES (31, 2, 'auto_generate', 0, 'completed', '354573e7-5b99-495d-a48b-e63f586c90cd', 100, NULL, '2026-04-21 18:36:57', '2026-04-21 18:42:47', NULL);

SET FOREIGN_KEY_CHECKS = 1;
