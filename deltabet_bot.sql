CREATE DATABASE IF NOT EXISTS `deltabet_bot` DEFAULT CHARACTER SET utf8;
USE `deltabet_bot`;

DROP TABLE IF EXISTS `Admins`;
CREATE TABLE IF NOT EXISTS `Admins` (
  `id` BIGINT,
  `first_name` TEXT DEFAULT NULL,
  `last_name` TEXT DEFAULT NULL,
  `username` TEXT UNIQUE DEFAULT NULL,
  `phone_number` TEXT DEFAULT NULL
  PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8;

INSERT INTO `Admins` (`id`, `first_name`, `last_name`, `username`, `phone_number`) VALUES
(303513097, 'Piero', 'Sepi', 'PieroSepi', NULL);
