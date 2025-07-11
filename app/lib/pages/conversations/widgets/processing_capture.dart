import 'package:flutter/material.dart';
import 'package:omi/backend/preferences.dart';
import 'package:omi/backend/schema/conversation.dart';
import 'package:omi/backend/schema/message_event.dart';
import 'package:omi/pages/capture/widgets/widgets.dart';
import 'package:omi/pages/conversations/widgets/capture.dart';
import 'package:omi/pages/conversation_capturing/page.dart';
import 'package:omi/pages/processing_conversations/page.dart';
import 'package:omi/providers/capture_provider.dart';
import 'package:omi/providers/connectivity_provider.dart';
import 'package:omi/providers/device_provider.dart';
import 'package:omi/providers/onboarding_provider.dart';
import 'package:omi/utils/analytics/mixpanel.dart';
import 'package:omi/utils/enums.dart';
import 'package:omi/utils/other/temp.dart';
import 'package:omi/utils/platform/platform_service.dart';
import 'package:omi/widgets/dialog.dart';
import 'package:provider/provider.dart';

class ConversationCaptureWidget extends StatefulWidget {
  const ConversationCaptureWidget({super.key});

  @override
  State<ConversationCaptureWidget> createState() => _ConversationCaptureWidgetState();
}

class _ConversationCaptureWidgetState extends State<ConversationCaptureWidget> {
  @override
  Widget build(BuildContext context) {
    return Consumer3<CaptureProvider, DeviceProvider, ConnectivityProvider>(
        builder: (context, provider, deviceProvider, connectivityProvider, child) {
      var topConvoId = (provider.conversationProvider?.conversations ?? []).isNotEmpty
          ? provider.conversationProvider!.conversations.first.id
          : null;

      var header = _getConversationHeader(context);
      if (header == null) {
        return const SizedBox.shrink();
      }

      return GestureDetector(
        onTap: () async {
          if (provider.segments.isEmpty && provider.photos.isEmpty) return;
          routeToPage(context, ConversationCapturingPage(topConversationId: topConvoId));
        },
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 16),
          width: double.maxFinite,
          decoration: BoxDecoration(
            color: Colors.grey.shade900,
            borderRadius: BorderRadius.circular(16.0),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                header,
                (provider.segments.isNotEmpty || provider.photos.isNotEmpty)
                    ? const Column(
                        children: [
                          SizedBox(height: 8),
                          LiteCaptureWidget(),
                          SizedBox(height: 8),
                        ],
                      )
                    : const SizedBox.shrink(),
              ],
            ),
          ),
        ),
      );
    });
  }

  _toggleRecording(BuildContext context, CaptureProvider provider) async {
    var recordingState = provider.recordingState;

    if (PlatformService.isDesktop) {
      final onboardingProvider = context.read<OnboardingProvider>();
      if (!onboardingProvider.hasMicrophonePermission) {
        bool granted = await onboardingProvider.askForMicrophonePermissions();
        if (!granted) {
          return;
        }
      }
      if (recordingState == RecordingState.systemAudioRecord) {
        await provider.stopSystemAudioRecording();
        // MixpanelManager().track("System Audio Recording Stopped");
      } else if (recordingState == RecordingState.initialising) {
        debugPrint('initialising, have to wait');
      } else {
        await provider.streamSystemAudioRecording();
        // MixpanelManager().track("System Audio Recording Started");
      }
    } else {
      // Existing phone mic logic
      if (recordingState == RecordingState.record) {
        await provider.stopStreamRecording();
        MixpanelManager().phoneMicRecordingStopped();
      } else if (recordingState == RecordingState.initialising) {
        debugPrint('initialising, have to wait');
      } else {
        showDialog(
          context: context,
          builder: (c) => getDialog(
            context,
            () => Navigator.pop(context),
            () async {
              Navigator.pop(context);
              await provider.streamRecording();
              MixpanelManager().phoneMicRecordingStarted();
            },
            'Limited Capabilities',
            'Recording with your phone microphone has a few limitations, including but not limited to: speaker profiles, background reliability.',
            okButtonText: 'Ok, I understand',
          ),
        );
      }
    }
  }

  Widget? _getConversationHeader(BuildContext context) {
    var captureProvider = context.read<CaptureProvider>();
    var connectivityProvider = context.read<ConnectivityProvider>();

    bool internetConnectionStateOk = connectivityProvider.isConnected;
    bool deviceServiceStateOk = captureProvider.recordingDeviceServiceReady;
    bool transcriptServiceStateOk = captureProvider.transcriptServiceReady;
    bool isHavingTranscript = captureProvider.segments.isNotEmpty;
    bool isHavingPhotos = captureProvider.photos.isNotEmpty;
    bool isHavingDesireDevice = SharedPreferencesUtil().btDevice.id.isNotEmpty;
    bool isHavingRecordingDevice = captureProvider.havingRecordingDevice;

    bool isUsingPhoneMic = captureProvider.recordingState == RecordingState.record ||
        captureProvider.recordingState == RecordingState.initialising ||
        captureProvider.recordingState == RecordingState.pause;

    // Left
    Widget? left;
    if (isUsingPhoneMic || !isHavingDesireDevice) {
      left = Center(
        child: getPhoneMicRecordingButton(
          context,
          () => _toggleRecording(context, captureProvider),
          captureProvider.recordingState,
        ),
      );
    } else if (!deviceServiceStateOk && !transcriptServiceStateOk && !isHavingTranscript && !isHavingDesireDevice) {
      return null; // not using phone mic, not ready
    } else if (!deviceServiceStateOk) {
      left = Row(
        children: [
          const Icon(Icons.record_voice_over),
          const SizedBox(width: 12),
          Container(
            decoration: BoxDecoration(
              color: Colors.grey.shade800,
              borderRadius: BorderRadius.circular(16),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: Text(
              'Waiting for device...',
              style: Theme.of(context).textTheme.bodyMedium!.copyWith(color: Colors.white),
              maxLines: 1,
            ),
          ),
        ],
      );
    } else {
      left = Row(
        children: [
          const Icon(Icons.record_voice_over),
          const SizedBox(width: 12),
          Container(
            decoration: BoxDecoration(
              color: Colors.grey.shade800,
              borderRadius: BorderRadius.circular(16),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: Text(
              (isHavingTranscript || isHavingPhotos) ? 'In progress...' : 'Say something...',
              style: Theme.of(context).textTheme.bodyMedium!.copyWith(color: Colors.white),
              maxLines: 1,
            ),
          ),
        ],
      );
    }

    // Right
    Widget? statusIndicator;
    var stateText = "";
    if (!isHavingRecordingDevice && !isUsingPhoneMic) {
      stateText = "";
    } else if (transcriptServiceStateOk && (isUsingPhoneMic || isHavingRecordingDevice)) {
      var lastEvent = captureProvider.transcriptionServiceStatuses.lastOrNull;
      if (lastEvent is MessageServiceStatusEvent) {
        if (lastEvent.status == "ready") {
          stateText = "Listening";
          statusIndicator = const RecordingStatusIndicator();
        } else {
          bool transcriptionDiagnosticEnabled = SharedPreferencesUtil().transcriptionDiagnosticEnabled;
          stateText = transcriptionDiagnosticEnabled ? (lastEvent.statusText ?? "") : "Connecting";
        }
      } else {
        stateText = "Connecting";
      }
    } else if (!internetConnectionStateOk) {
      stateText = "Waiting for network";
    } else if (!transcriptServiceStateOk) {
      stateText = "Connecting";
    }
    Widget right = stateText.isNotEmpty || statusIndicator != null
        ? Expanded(
            child: Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              Text(
                stateText,
                style: TextStyle(color: Colors.grey.shade400, fontSize: 14),
                maxLines: 1,
                textAlign: TextAlign.end,
              ),
              if (statusIndicator != null) ...[
                const SizedBox(width: 8),
                SizedBox(
                  width: 16,
                  height: 16,
                  child: statusIndicator,
                )
              ],
            ],
          ))
        : const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(left: 0, right: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          left,
          right,
        ],
      ),
    );
  }
}

class RecordingStatusIndicator extends StatefulWidget {
  const RecordingStatusIndicator({super.key});

  @override
  State<RecordingStatusIndicator> createState() => _RecordingStatusIndicatorState();
}

class _RecordingStatusIndicatorState extends State<RecordingStatusIndicator> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _opacityAnim;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1000), // Blink every half second
      vsync: this,
    )..repeat(reverse: true);
    _opacityAnim = Tween<double>(begin: 1.0, end: 0.2).animate(_controller);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _opacityAnim,
      child: const Icon(Icons.fiber_manual_record, color: Colors.red, size: 16.0),
    );
  }
}

getPhoneMicRecordingButton(BuildContext context, VoidCallback toggleRecordingCb, RecordingState currentActualState) {
  if (SharedPreferencesUtil().btDevice.id.isNotEmpty && (!PlatformService.isDesktop)) {
    // If a BT device is configured and we are NOT on desktop, don't show this button.
    return const SizedBox.shrink();
  }
  // If on desktop, AND a BT device is connected, this button should still be hidden
  // as the primary interaction should be via the BT device, not system audio as a fallback to phone mic.
  // This button is primarily for when NO BT device is the target.
  final deviceProvider = Provider.of<DeviceProvider>(context, listen: false);
  if (PlatformService.isDesktop &&
      deviceProvider.connectedDevice != null &&
      SharedPreferencesUtil().btDevice.id == deviceProvider.connectedDevice!.id) {
    return const SizedBox.shrink();
  }

  final bool isDesktop = PlatformService.isDesktop;
  String text;
  Widget icon;
  bool isLoading = currentActualState == RecordingState.initialising;

  if (isDesktop) {
    if (isLoading) {
      text = 'Initialising System Audio';
      icon = const SizedBox(
        height: 8,
        width: 8,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          color: Colors.white,
        ),
      );
    } else if (currentActualState == RecordingState.systemAudioRecord) {
      text = 'Stop Recording';
      icon = const Icon(Icons.stop, color: Colors.red, size: 12);
    } else {
      text = 'Start Recording';
      icon = const Icon(Icons.mic, size: 18);
    }
  } else {
    // Phone Mic
    if (isLoading) {
      text = 'Initialising Recorder';
      icon = const SizedBox(
        height: 8,
        width: 8,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          color: Colors.white,
        ),
      );
    } else if (currentActualState == RecordingState.record) {
      text = 'Stop Recording';
      icon = const Icon(Icons.stop, color: Colors.red, size: 12);
    } else {
      text = 'Try With Phone Mic';
      icon = const Icon(Icons.mic, size: 18);
    }
  }

  return MaterialButton(
    onPressed: isLoading ? null : toggleRecordingCb,
    child: Row(
      mainAxisSize: MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.start,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        icon,
        const SizedBox(width: 4),
        Text(
          text,
          style: Theme.of(context).textTheme.bodyMedium!.copyWith(color: Colors.white, fontWeight: FontWeight.w500),
        ),
        const SizedBox(width: 4),
      ],
    ),
  );
}

Widget getProcessingConversationsWidget(List<ServerConversation> conversations) {
  // FIXME, this has to be a single one always, and also a conversation obj
  if (conversations.isEmpty) {
    return const SliverToBoxAdapter(child: SizedBox.shrink());
  }
  return SliverList(
    delegate: SliverChildBuilderDelegate(
      (context, index) {
        var pm = conversations[index];
        return Padding(
          padding: const EdgeInsets.fromLTRB(0, 20, 0, 0),
          child: ProcessingConversationWidget(conversation: pm),
        );
      },
      childCount: conversations.length,
    ),
  );
}

// PROCESSING CONVERSATION

class ProcessingConversationWidget extends StatefulWidget {
  final ServerConversation conversation;

  const ProcessingConversationWidget({
    super.key,
    required this.conversation,
  });

  @override
  State<ProcessingConversationWidget> createState() => _ProcessingConversationWidgetState();
}

class _ProcessingConversationWidgetState extends State<ProcessingConversationWidget> {
  @override
  Widget build(BuildContext context) {
    return Consumer3<CaptureProvider, DeviceProvider, ConnectivityProvider>(
        builder: (context, provider, deviceProvider, connectivityProvider, child) {
      return GestureDetector(
          onTap: () async {
            routeToPage(
              context,
              ProcessingConversationPage(
                conversation: widget.conversation,
              ),
            );
          },
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            width: double.maxFinite,
            decoration: BoxDecoration(
              color: Colors.grey.shade900,
              borderRadius: BorderRadius.circular(16.0),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _getConversationHeader(context),
                  (widget.conversation.transcriptSegments.isNotEmpty || widget.conversation.photos.isNotEmpty)
                      ? Column(
                          children: [
                            const SizedBox(height: 8),
                            getLiteTranscriptWidget(
                              widget.conversation.transcriptSegments,
                              widget.conversation.photos,
                              null,
                            ),
                            const SizedBox(height: 8),
                          ],
                        )
                      : const SizedBox.shrink(),
                ],
              ),
            ),
          ));
    });
  }

  _getConversationHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 0, right: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                ),
              ),
              const SizedBox(width: 20),
              Container(
                decoration: BoxDecoration(
                  color: Colors.grey.shade800,
                  borderRadius: BorderRadius.circular(16),
                ),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                child: Text(
                  'Processing',
                  style: Theme.of(context).textTheme.bodyMedium!.copyWith(color: Colors.white),
                  maxLines: 1,
                ),
              ),
            ],
          )
        ],
      ),
    );
  }
}
