package io.github.pulquero.rotordroid;

import androidx.appcompat.app.AppCompatActivity;
import butterknife.BindColor;
import butterknife.BindView;
import butterknife.ButterKnife;
import butterknife.OnCheckedChanged;
import butterknife.OnTextChanged;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbManager;
import android.os.Bundle;
import android.os.SystemClock;
import android.text.Editable;
import android.text.TextWatcher;
import android.widget.EditText;
import android.widget.Switch;
import android.widget.TextView;

import com.androidplot.util.PixelUtils;
import com.androidplot.util.Redrawer;
import com.androidplot.xy.BoundaryMode;
import com.androidplot.xy.FastLineAndPointRenderer;
import com.androidplot.xy.PanZoom;
import com.androidplot.xy.StepMode;
import com.androidplot.xy.XYGraphWidget;
import com.androidplot.xy.XYPlot;
import com.androidplot.xy.XYSeries;
import com.hoho.android.usbserial.driver.UsbSerialDriver;
import com.hoho.android.usbserial.driver.UsbSerialPort;
import com.hoho.android.usbserial.driver.UsbSerialProber;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;

public class MainActivity extends AppCompatActivity {
    private static final int MIN_FREQ = 5645;
    private static final int MAX_FREQ = 5945;
    private static final int TIMEOUT = 100;
    private static final long SCAN_UPDATE_INTERVAL = 100L;
    private static final int SCAN_STEP = 2;
    private static final long SIGNAL_UPDATE_INTERVAL = 50L;
    private static final int NUM_SAMPLES = 200;
    private static final byte READ_FREQUENCY = 0x03;
    private static final byte READ_LAP_STATS = 0x05;
    private static final byte WRITE_FREQUENCY = 0x51;
    private ScheduledExecutorService executor;
    private Future<UsbSerialPort> fPort;
    private Callable<ScheduledFuture<?>> acquisitionStarter;
    private ScheduledFuture<?> fStarter;

    private FixedXYSeries spectrumSeries;
    private FixedXYSeries minSeries;
    private FixedXYSeries maxSeries;
    private CircularXYSeries rssiSeries;
    private CircularXYSeries historySeries;
    private Redrawer redrawer;
    private long startTime;

    @BindColor(R.color.spectrum)
    int spectrumColor;
    @BindColor(R.color.min)
    int minColor;
    @BindColor(R.color.max)
    int maxColor;
    @BindColor(R.color.rssi)
    int rssiColor;
    @BindColor(R.color.history)
    int historyColor;

    @BindView(R.id.freqSelector)
    EditText freqSelector;
    @BindView(R.id.scanSwitch)
    Switch scanSwitch;
    @BindView(R.id.plot)
    XYPlot plot;
    @BindView(R.id.messages)
    TextView msgLabel;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        ButterKnife.bind(this);
        plot.setRangeBoundaries(0, 150, BoundaryMode.FIXED);
        plot.setRangeStep(StepMode.INCREMENT_BY_VAL, 10.0);
        plot.getGraph().getLineLabelStyle(XYGraphWidget.Edge.BOTTOM).getPaint().setTextSize(PixelUtils.spToPix(10.0f));
        plot.getGraph().getLineLabelStyle(XYGraphWidget.Edge.LEFT).getPaint().setTextSize(PixelUtils.spToPix(10.0f));
        plot.getLegend().getTextPaint().setTextSize(PixelUtils.spToPix(10.0f));
        PanZoom.attach(plot);
        redrawer = new Redrawer(plot, 25, false);
        executor = Executors.newSingleThreadScheduledExecutor();
        fPort = executor.submit(() -> openSerialPort());
        acquisitionStarter = scanAcquisition();
    }

    @Override
    protected void onStart() {
        super.onStart();
        if (rssiSeries != null) {
            rssiSeries.reset();
        }
        if (historySeries != null) {
            historySeries.reset();
        }
        startTime = SystemClock.elapsedRealtime();
        executor.execute(() -> {
            try {
                UsbSerialPort port = fPort.get();
                int freq = readFrequency(port);
                String freqValue = Integer.toString(freq);
                runOnUiThread(() -> freqSelector.setText(freqValue));
            } catch (ExecutionException | InterruptedException | IOException ex) {
                runOnUiThread(() -> msgLabel.setText(ex.getMessage()));
            }
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        redrawer.start();
        try {
            fStarter = acquisitionStarter.call();
        } catch (Exception ex) {
            runOnUiThread(() -> msgLabel.setText(ex.getMessage()));
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (fStarter != null) {
            fStarter.cancel(true);
            fStarter = null;
        }
        redrawer.pause();
        clearSeries();
    }

    @Override
    protected void onStop() {
        super.onStop();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        try {
            UsbSerialPort port = fPort.get();
            port.close();
        } catch (ExecutionException | InterruptedException | IOException ignore) {
        }
        executor.shutdown();
    }

    private Callable<ScheduledFuture<?>> scanAcquisition() {
        return () -> {
            clearSeries();
            plot.setDomainStep(StepMode.INCREMENT_BY_VAL, 25.0);
            plot.setDomainBoundaries(MIN_FREQ+5, MAX_FREQ+5, BoundaryMode.FIXED);
            minSeries = new FixedXYSeries("Min", MIN_FREQ, SCAN_STEP, (MAX_FREQ - MIN_FREQ)/SCAN_STEP + 1);
            plot.addSeries(minSeries, new FastLineAndPointRenderer.Formatter(minColor, null, null));
            maxSeries = new FixedXYSeries("Max", MIN_FREQ, SCAN_STEP, (MAX_FREQ - MIN_FREQ)/SCAN_STEP + 1);
            plot.addSeries(maxSeries, new FastLineAndPointRenderer.Formatter(maxColor, null, null));
            spectrumSeries = new FixedXYSeries("Live", MIN_FREQ, SCAN_STEP, (MAX_FREQ - MIN_FREQ)/SCAN_STEP + 1);
            plot.addSeries(spectrumSeries, new FastLineAndPointRenderer.Formatter(spectrumColor, null, null));
            plot.getGraph().setLineLabelRenderer(XYGraphWidget.Edge.BOTTOM, new XYGraphWidget.LineLabelRenderer());
            return executor.scheduleWithFixedDelay(() -> {
                try {
                    UsbSerialPort port = fPort.get();
                    int freq = readFrequency(port);
                    LapStats stats = readLapStats(port, currentTime());

                    spectrumSeries.set(freq, stats.rssi);
                    minSeries.set(freq, minSeries.at(freq) == 0 ? stats.rssi : Math.min(stats.rssi, minSeries.at(freq)));
                    maxSeries.set(freq, Math.max(stats.rssi, maxSeries.at(freq)));
                    freq+=SCAN_STEP;
                    if (freq > MAX_FREQ) {
                        freq = MIN_FREQ;
                    }
                    writeFrequency(port, freq);
                    String freqValue = Integer.toString(freq);
                    runOnUiThread(() -> freqSelector.setText(freqValue));
                } catch (ExecutionException | InterruptedException | IOException ex) {
                    runOnUiThread(() -> msgLabel.setText(ex.getMessage()));
                }
            }, 0L, SCAN_UPDATE_INTERVAL, TimeUnit.MILLISECONDS);
        };
    }

    private Callable<ScheduledFuture<?>> signalAcquisition() {
        return () -> {
            clearSeries();
            plot.setDomainStep(StepMode.INCREMENT_BY_VAL, 1000.0);
            long time = currentTime();
            plot.setDomainBoundaries(time - NUM_SAMPLES*SIGNAL_UPDATE_INTERVAL, time, BoundaryMode.FIXED);
            rssiSeries = new CircularXYSeries("Live", NUM_SAMPLES);
            plot.addSeries(rssiSeries, new FastLineAndPointRenderer.Formatter(rssiColor, null, null));
            historySeries = new CircularXYSeries("History", NUM_SAMPLES);
            plot.addSeries(historySeries, new FastLineAndPointRenderer.Formatter(historyColor, null, null));
            plot.getGraph().setLineLabelRenderer(XYGraphWidget.Edge.BOTTOM, new XYGraphWidget.LineLabelRenderer() {
                @Override
                protected void drawLabel(Canvas canvas, String text, Paint paint, float x, float y, boolean isOrigin) {
                }
            });
            return executor.scheduleWithFixedDelay(() -> {
                try {
                    UsbSerialPort port = fPort.get();
                    long currentTime = currentTime();
                    LapStats stats = readLapStats(port, currentTime);

                    rssiSeries.add(stats.t, stats.rssi);
                    if(stats.historyRssi != 0) {
                        historySeries.add(stats.t - stats.msSinceHistoryStart, stats.historyRssi);
                        if (stats.msSinceHistoryStart != stats.msSinceHistoryEnd) {
                            historySeries.add(stats.t - stats.msSinceHistoryEnd, stats.historyRssi);
                        }
                    }
                    runOnUiThread(() -> {
                        plot.setDomainBoundaries(currentTime - NUM_SAMPLES*SIGNAL_UPDATE_INTERVAL, currentTime, BoundaryMode.FIXED);
                    });
                } catch (ExecutionException | InterruptedException | IOException ex) {
                    runOnUiThread(() -> msgLabel.setText(ex.getMessage()));
                }
            }, 0L, SIGNAL_UPDATE_INTERVAL, TimeUnit.MILLISECONDS);
        };
    }

    private int currentTime() {
        return (int) (SystemClock.elapsedRealtime() - startTime);
    }

    @OnCheckedChanged(R.id.scanSwitch)
    public void onScanSwitch() {
        fStarter.cancel(true);
        if(scanSwitch.isChecked()) {
            freqSelector.setEnabled(false);
            freqSelector.removeTextChangedListener(updateFrequencyListener);
            acquisitionStarter = scanAcquisition();
        } else {
            freqSelector.addTextChangedListener(updateFrequencyListener);
            freqSelector.setEnabled(true);
            acquisitionStarter = signalAcquisition();
        }
        clearSeries();
        try {
            fStarter = acquisitionStarter.call();
        } catch (Exception ex) {
            runOnUiThread(() -> msgLabel.setText(ex.getMessage()));
        }
    }

    private void clearSeries() {
        if (spectrumSeries != null) {
            plot.removeSeries(spectrumSeries);
            spectrumSeries = null;
        }
        if (minSeries != null) {
            plot.removeSeries(minSeries);
            minSeries = null;
        }
        if (maxSeries != null) {
            plot.removeSeries(maxSeries);
            maxSeries = null;
        }
        if (rssiSeries != null) {
            plot.removeSeries(rssiSeries);
            rssiSeries = null;
        }
        if (historySeries != null) {
            plot.removeSeries(historySeries);
            historySeries = null;
        }
    }

    final TextWatcher updateFrequencyListener = new TextWatcher() {
        @Override
        public void beforeTextChanged(CharSequence s, int start, int count, int after) {
        }

        @Override
        public void onTextChanged(CharSequence s, int start, int before, int count) {
        }

        @Override
        public void afterTextChanged(Editable editable) {
            String freqValue = editable.toString();
            if (freqValue.isEmpty()) {
                return;
            }
            int freq = Integer.parseInt(freqValue);
            if (freq >= MIN_FREQ && freq <= MAX_FREQ) {
                if(rssiSeries != null) {
                    plot.removeSeries(rssiSeries);
                }
                if (historySeries != null) {
                    plot.removeSeries(historySeries);
                }
                executor.execute(() -> {
                    try {
                        UsbSerialPort port = fPort.get();
                        writeFrequency(port, freq);
                        if (rssiSeries != null) {
                            rssiSeries.reset();
                        }
                        if (historySeries != null) {
                            historySeries.reset();
                        }
                    } catch (ExecutionException | InterruptedException | IOException ex) {
                        runOnUiThread(() -> msgLabel.setText(ex.getMessage()));
                    }
                });
                if(rssiSeries != null) {
                    plot.addSeries(rssiSeries, new FastLineAndPointRenderer.Formatter(rssiColor, null, null));
                }
                if (historySeries != null) {
                    plot.addSeries(historySeries, new FastLineAndPointRenderer.Formatter(historyColor, null, null));
                }
            }
        }
    };


    private UsbSerialPort openSerialPort() throws IOException {
        UsbManager manager = (UsbManager) getSystemService(Context.USB_SERVICE);
        List<UsbSerialDriver> availableDrivers = UsbSerialProber.getDefaultProber().findAllDrivers(manager);
        if (availableDrivers.isEmpty()) {
            throw new IOException("No compatible USB devices");
        }

        // Open a connection to the first available driver.
        UsbSerialDriver driver = availableDrivers.get(0);
        if (!manager.hasPermission(driver.getDevice())) {
            throw new IOException("No permission for USB device");
        }
        UsbDeviceConnection connection = manager.openDevice(driver.getDevice());
        if (connection == null) {
            throw new IOException("Failed to open USB device");
        }

        UsbSerialPort port = driver.getPorts().get(0); // Most devices have just one fPort (fPort 0)
        port.open(connection);
        port.setParameters(115200, UsbSerialPort.DATABITS_8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE);
        try {
            Thread.sleep(2000);
        } catch (InterruptedException e) {
        }
        return port;
    }

    private static void writeFrequency(UsbSerialPort port, int freq) throws IOException {
        byte[] writeFreqCmd = writeCommand(WRITE_FREQUENCY, 2);
        write16(writeFreqCmd, 1, freq);
        addChecksum(writeFreqCmd);
        port.write(writeFreqCmd, TIMEOUT);
    }

    private static int readFrequency(UsbSerialPort port) throws IOException {
        byte[] buf = readCommand(port, READ_FREQUENCY, 2);
        return read16(buf, 0);
    }

    private static LapStats readLapStats(UsbSerialPort port, long currentTime) throws IOException {
        LapStats stats = new LapStats();
        long sendTime = System.nanoTime();
        byte[] buf = readCommand(port, READ_LAP_STATS, 16);
        long recvTime = System.nanoTime();
        long delayMs = TimeUnit.NANOSECONDS.toMillis((recvTime - sendTime)/2);
        stats.t = (int) (currentTime + delayMs);
        byte laps = buf[0];
        int msSinceLastLap = read16(buf, 1);
        stats.rssi = buf[3];
        byte peakRssi = buf[4];
        byte lastPassPeak = buf[5];
        int loopTimeMicros = read16(buf, 6);
        byte flags = buf[8];
        byte lastPassNadir = buf[9];
        byte nadirRssi = buf[10];
        stats.historyRssi = buf[11];
        stats.msSinceHistoryStart = read16(buf, 12);
        stats.msSinceHistoryEnd = read16(buf, 14);
        return stats;
    }

    private static byte[] readCommand(UsbSerialPort port, byte cmd, int payloadSize) throws IOException {
        port.write(new byte[] {cmd}, TIMEOUT);
        byte[] buf = new byte[20];
        int len = port.read(buf, TIMEOUT);
        if (len != payloadSize+1) {
            throw new IOException(String.format("%h: Unexpected response size %d", cmd, len));
        }
        byte checksum = buf[payloadSize];
        byte expectedChecksum = calculateChecksum(buf, 0, len-1);
        if (checksum != expectedChecksum) {
            throw new IOException(String.format("%h: Invalid checksum", cmd));
        }
        return buf;
    }

    private static byte[] writeCommand(byte cmd, int payloadSize) {
        byte[] buf = new byte[1+payloadSize+1];
        buf[0] = cmd;
        return buf;
    }

    private static int write16(byte[] buf, int pos, int data) {
        buf[pos++] = (byte) (data >> 8);
        buf[pos++] = (byte) (data & 0xFF);
        return pos;
    }

    private static int read16(byte[] buf, int pos) {
        int result = buf[pos++];
        result = (result << 8) | (buf[pos++] & 0xFF);
        return result;
    }

    private static byte calculateChecksum(byte[] buf, int start, int len) {
        int checksum = 0;
        for(int i=start; i<start+len; i++) {
            checksum += (buf[i] & 0xFF);
        }
        return (byte) (checksum & 0xFF);
    }

    private static void addChecksum(byte[] buf) {
        byte checksum = calculateChecksum(buf, 1, buf.length-2);
        buf[buf.length-1] = checksum;
    }


    static final class LapStats {
        int t;
        int rssi;
        int historyRssi;
        int msSinceHistoryStart;
        int msSinceHistoryEnd;
    }

    static final class FixedXYSeries implements XYSeries {
        final String title;
        final int[] yVals;
        final int xOffset;
        final int xFactor;

        FixedXYSeries(String title, int offset, int factor, int size) {
            this.title = title;
            this.yVals = new int[size];
            this.xOffset = offset;
            this.xFactor = factor;
        }

        public void set(int x, int y) {
            yVals[(x-xOffset)/xFactor] = y;
        }

        public int at(int x) {
            return yVals[(x-xOffset)/xFactor];
        }

        @Override
        public int size() {
            return yVals.length;
        }

        @Override
        public Number getX(int index) {
            return xFactor*index+xOffset;
        }

        @Override
        public Number getY(int index) {
            return yVals[index];
        }

        @Override
        public String getTitle() {
            return title;
        }
    }

    static final class CircularXYSeries implements XYSeries {
        final String title;
        final int[] xVals;
        final int[] yVals;
        int head;
        int tail;
        int size;

        CircularXYSeries(String title, int size) {
            this.title = title;
            this.xVals = new int[size];
            this.yVals = new int[size];
        }

        public void add(int x, int y) {
            if(size < xVals.length) {
                size++;
            } else {
                if(tail >= size) {
                    tail = 0;
                }
                head = tail + 1;
                if(head >= size) {
                    head = 0;
                }
            }
            xVals[tail] = x;
            yVals[tail] = y;
            tail++;
        }

        @Override
        public int size() {
            return size;
        }

        @Override
        public Number getX(int index) {
            return xVals[(head+index) % size];
        }

        @Override
        public Number getY(int index) {
            return yVals[(head+index) % size];
        }

        @Override
        public String getTitle() {
            return title;
        }

        public void reset() {
            head = 0;
            tail = 0;
            size = 0;
        }
    }
}
