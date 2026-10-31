/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19-11.4.13-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: sglab
-- ------------------------------------------------------
-- Server version	11.4.13-MariaDB-ubu2404

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Current Database: `sglab`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `sglab` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;

USE `sglab`;

--
-- Table structure for table `comentario`
--

DROP TABLE IF EXISTS `comentario`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `comentario` (
  `id_comentario` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `id_equipo` int(10) unsigned NOT NULL,
  `autor_ci` int(10) unsigned NOT NULL,
  `contenido` text NOT NULL,
  `fecha_hora` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_comentario`),
  KEY `idx_comentario_equipo_fecha` (`id_equipo`,`fecha_hora`),
  KEY `fk_comentario_autor` (`autor_ci`),
  CONSTRAINT `fk_comentario_autor` FOREIGN KEY (`autor_ci`) REFERENCES `usuarios` (`ci`),
  CONSTRAINT `fk_comentario_equipo` FOREIGN KEY (`id_equipo`) REFERENCES `equipo` (`id_equipo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `comentario`
--

LOCK TABLES `comentario` WRITE;
/*!40000 ALTER TABLE `comentario` DISABLE KEYS */;
/*!40000 ALTER TABLE `comentario` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `equipo`
--

DROP TABLE IF EXISTS `equipo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `equipo` (
  `id_equipo` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `num_serie` varchar(100) DEFAULT NULL,
  `smbios_uuid` char(36) DEFAULT NULL,
  `estado_administrativo` enum('OPERATIVA','EN_REPARACION','FUERA_DE_SERVICIO') NOT NULL DEFAULT 'OPERATIVA',
  `hostname` varchar(255) DEFAULT NULL,
  `mac` char(17) DEFAULT NULL,
  `cpu` varchar(255) DEFAULT NULL,
  `ram_gb` decimal(10,2) unsigned DEFAULT NULL,
  `disco_tipo` varchar(30) DEFAULT NULL,
  `disco_total_gb` decimal(12,2) unsigned DEFAULT NULL,
  `id_laboratorio` int(10) unsigned DEFAULT NULL,
  PRIMARY KEY (`id_equipo`),
  UNIQUE KEY `uq_equipo_num_serie` (`num_serie`),
  UNIQUE KEY `uq_equipo_smbios_uuid` (`smbios_uuid`),
  KEY `fk_equipo_laboratorio` (`id_laboratorio`),
  CONSTRAINT `fk_equipo_laboratorio` FOREIGN KEY (`id_laboratorio`) REFERENCES `laboratorio` (`id_laboratorio`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `equipo`
--

LOCK TABLES `equipo` WRITE;
/*!40000 ALTER TABLE `equipo` DISABLE KEYS */;
/*!40000 ALTER TABLE `equipo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `laboratorio`
--

DROP TABLE IF EXISTS `laboratorio`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `laboratorio` (
  `id_laboratorio` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  PRIMARY KEY (`id_laboratorio`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `laboratorio`
--

LOCK TABLES `laboratorio` WRITE;
/*!40000 ALTER TABLE `laboratorio` DISABLE KEYS */;
/*!40000 ALTER TABLE `laboratorio` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `registro`
--

DROP TABLE IF EXISTS `registro`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `registro` (
  `id_registro` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `id_equipo` int(10) unsigned NOT NULL,
  `usuario_ci` int(10) unsigned DEFAULT NULL,
  `id_ejecucion` char(36) DEFAULT NULL,
  `hash_archivo` char(64) DEFAULT NULL,
  `fecha_recepcion` datetime NOT NULL DEFAULT current_timestamp(),
  `hostname_reportado` varchar(255) DEFAULT NULL,
  `sistema_operativo` varchar(255) DEFAULT NULL,
  `cpu` varchar(255) DEFAULT NULL,
  `ram_gb` decimal(10,2) unsigned DEFAULT NULL,
  `mac` char(17) DEFAULT NULL,
  `id_laboratorio_observado` int(10) unsigned DEFAULT NULL,
  `fecha` datetime NOT NULL DEFAULT current_timestamp(),
  `nombre` varchar(255) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `estado` enum('OK','ERROR') NOT NULL,
  `disco_libre_gb` decimal(12,2) unsigned DEFAULT NULL,
  PRIMARY KEY (`id_registro`),
  UNIQUE KEY `uq_registro_id_ejecucion` (`id_ejecucion`),
  KEY `fk_registro_laboratorio` (`id_laboratorio_observado`),
  KEY `idx_registro_equipo_fecha` (`id_equipo`,`fecha`),
  KEY `fk_registro_usuario` (`usuario_ci`),
  CONSTRAINT `fk_registro_equipo` FOREIGN KEY (`id_equipo`) REFERENCES `equipo` (`id_equipo`),
  CONSTRAINT `fk_registro_laboratorio` FOREIGN KEY (`id_laboratorio_observado`) REFERENCES `laboratorio` (`id_laboratorio`),
  CONSTRAINT `fk_registro_usuario` FOREIGN KEY (`usuario_ci`) REFERENCES `usuarios` (`ci`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `registro`
--

LOCK TABLES `registro` WRITE;
/*!40000 ALTER TABLE `registro` DISABLE KEYS */;
/*!40000 ALTER TABLE `registro` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `registro_disco`
--

DROP TABLE IF EXISTS `registro_disco`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `registro_disco` (
  `id_registro` bigint(20) unsigned NOT NULL,
  `orden` smallint(5) unsigned NOT NULL,
  `dispositivo` varchar(255) DEFAULT NULL,
  `modelo` varchar(255) DEFAULT NULL,
  `num_serie` varchar(255) DEFAULT NULL,
  `tipo` enum('HDD','SSD','OTRO') DEFAULT NULL,
  `capacidad_total_gb` decimal(12,2) unsigned DEFAULT NULL,
  PRIMARY KEY (`id_registro`,`orden`),
  CONSTRAINT `fk_disco_registro` FOREIGN KEY (`id_registro`) REFERENCES `registro` (`id_registro`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `registro_disco`
--

LOCK TABLES `registro_disco` WRITE;
/*!40000 ALTER TABLE `registro_disco` DISABLE KEYS */;
/*!40000 ALTER TABLE `registro_disco` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `registro_sistema_archivos`
--

DROP TABLE IF EXISTS `registro_sistema_archivos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `registro_sistema_archivos` (
  `id_registro` bigint(20) unsigned NOT NULL,
  `orden` smallint(5) unsigned NOT NULL,
  `orden_disco` smallint(5) unsigned DEFAULT NULL,
  `dispositivo` varchar(255) DEFAULT NULL,
  `punto_montaje` varchar(1024) DEFAULT NULL,
  `tipo` varchar(50) DEFAULT NULL,
  `capacidad_total_gb` decimal(12,2) unsigned DEFAULT NULL,
  `espacio_libre_gb` decimal(12,2) unsigned DEFAULT NULL,
  PRIMARY KEY (`id_registro`,`orden`),
  KEY `fk_fs_disco` (`id_registro`,`orden_disco`),
  CONSTRAINT `fk_fs_disco` FOREIGN KEY (`id_registro`, `orden_disco`) REFERENCES `registro_disco` (`id_registro`, `orden`),
  CONSTRAINT `fk_fs_registro` FOREIGN KEY (`id_registro`) REFERENCES `registro` (`id_registro`),
  CONSTRAINT `ck_fs_espacio` CHECK (`espacio_libre_gb` is null or `capacidad_total_gb` is null or `espacio_libre_gb` <= `capacidad_total_gb`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `registro_sistema_archivos`
--

LOCK TABLES `registro_sistema_archivos` WRITE;
/*!40000 ALTER TABLE `registro_sistema_archivos` DISABLE KEYS */;
/*!40000 ALTER TABLE `registro_sistema_archivos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `ci` int(10) unsigned NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `apellido` varchar(100) NOT NULL,
  `correo` varchar(254) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `tipo_usuario` enum('ALUMNO','DOCENTE','ASISTENTE','ADMINISTRADOR') NOT NULL,
  PRIMARY KEY (`ci`),
  UNIQUE KEY `uq_usuarios_correo` (`correo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'sglab'
--

--
-- Dumping routines for database 'sglab'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed on 2026-10-28  5:16:13
