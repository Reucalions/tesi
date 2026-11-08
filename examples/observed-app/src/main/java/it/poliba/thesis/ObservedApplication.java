package it.poliba.thesis;

import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.logs.Severity;
import io.opentelemetry.exporter.logging.otlp.OtlpJsonLoggingLogRecordExporter;
import io.opentelemetry.sdk.logs.SdkLoggerProvider;
import io.opentelemetry.sdk.logs.export.SimpleLogRecordProcessor;
import io.opentelemetry.sdk.resources.Resource;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.HexFormat;
import java.util.UUID;
import java.util.Properties;
import java.util.jar.JarFile;
import java.util.concurrent.TimeUnit;
import java.util.logging.Formatter;
import java.util.logging.LogRecord;
import java.util.logging.StreamHandler;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.core.LoggerContext;

/**
 * Finite local workload: observes the selected loaded dependency and emits OTel logs.
 * No input version, exploit simulation, network listener or mitigation executor.
 */
public final class ObservedApplication {
    private ObservedApplication() {}

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            throw new IllegalArgumentException("Usage: ObservedApplication NEW_OTEL_FILE");
        }
        var context = (LoggerContext) LogManager.getContext(false);
        var log = context.getLogger(ObservedApplication.class.getName());
        String component = System.getProperty("thesis.observed.component", "log4j-core");
        Class<?> observedClass = switch (component) {
            case "log4j-core" -> LoggerContext.class;
            case "logback-core" -> Class.forName("ch.qos.logback.core.ContextBase");
            default -> throw new IllegalArgumentException("Unsupported observed component");
        };
        if (component.equals("logback-core")) {
            // Instantiate the library actually on this build's runtime classpath.
            observedClass.getConstructor().newInstance();
        }
        var loadedPackage = observedClass.getPackage();
        String title = loadedPackage.getImplementationTitle();
        String version = loadedPackage.getImplementationVersion();
        if (title == null || version == null) {
            throw new IllegalStateException("Loaded dependency lacks implementation metadata");
        }
        Path jar = Path.of(observedClass.getProtectionDomain().getCodeSource().getLocation().toURI());
        String observedName = title;
        if (component.equals("logback-core")) {
            // Artifact identity comes from the loaded JAR, not from a CTI alias or input label.
            try (var archive = new JarFile(jar.toFile())) {
                var entry = archive.getJarEntry("META-INF/maven/ch.qos.logback/logback-core/pom.properties");
                if (entry == null) throw new IllegalStateException("Missing loaded JAR Maven identity");
                var properties = new Properties();
                try (var stream = archive.getInputStream(entry)) { properties.load(stream); }
                if (!"ch.qos.logback".equals(properties.getProperty("groupId"))
                        || !component.equals(properties.getProperty("artifactId"))
                        || !version.equals(properties.getProperty("version"))) {
                    throw new IllegalStateException("Loaded Maven and implementation metadata differ");
                }
                observedName = properties.getProperty("artifactId");
            }
        }
        String sha256 = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(jar)));
        String instance = UUID.randomUUID().toString();
        var resource = Resource.create(Attributes.builder()
            .put("service.name", "thesis-observed-app")
            .put("service.instance.id", instance)
            .put("service.version", "1.0.0")
            .put("thesis.software.name", observedName)
            .put("thesis.software.manifest.title", title)
            .put("thesis.software.name.origin", component.equals("logback-core")
                ? "loaded-jar-maven-pom.properties" : "loaded-jar-implementation-title")
            .put("thesis.software.version", version)
            .put("thesis.software.jar.sha256", sha256)
            .put("thesis.workload.kind", "local-demonstration")
            .build());

        // Public SDK exporter emits one ResourceLogs object per JUL message.
        // The formatter adds only the batch envelope expected by the file gateway.
        var exporterLogger = java.util.logging.Logger.getLogger(
            OtlpJsonLoggingLogRecordExporter.class.getName());
        exporterLogger.setUseParentHandlers(false);
        var handler = new StreamHandler(
            Files.newOutputStream(Path.of(args[0]), StandardOpenOption.CREATE_NEW),
            new Formatter() {
                @Override public String format(LogRecord record) {
                    return "{\"resourceLogs\":[" + record.getMessage() + "]}\n";
                }
            }) {
                @Override public synchronized void publish(LogRecord record) {
                    super.publish(record);
                    flush();
                }
            };
        handler.setEncoding("UTF-8");
        exporterLogger.addHandler(handler);
        try (var provider = SdkLoggerProvider.builder().setResource(resource)
                .addLogRecordProcessor(SimpleLogRecordProcessor.create(
                    OtlpJsonLoggingLogRecordExporter.create())).build()) {
            var telemetry = provider.get("it.poliba.thesis.observed-app");
            for (int index = 0; index < 5; index++) {
                BigDecimal amount = BigDecimal.valueOf(index + 1).multiply(new BigDecimal("12.50"));
                log.info("Local demonstration item {} processed: {}", index, amount);
                Instant now = Instant.now();
                telemetry.logRecordBuilder()
                    .setTimestamp(now).setObservedTimestamp(now).setSeverity(Severity.INFO)
                    .setBody("Local demonstration item processed")
                    .setAttribute(io.opentelemetry.api.common.AttributeKey.longKey("thesis.workload.item"), (long) index)
                    .emit();
            }
            var flushed = provider.forceFlush().join(10, TimeUnit.SECONDS);
            if (!flushed.isSuccess()) {
                throw new IllegalStateException("OTel flush failed");
            }
        } finally {
            exporterLogger.removeHandler(handler);
            handler.close();
            LogManager.shutdown();
        }
        System.out.println("Observed " + observedName + " " + version + "; manifest=" + title + "; instance=" + instance);
    }
}
