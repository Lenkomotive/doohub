import 'dart:developer';

import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../models/pipeline_template.dart';
import '../../services/api.dart';

class TemplatesState extends Equatable {
  final List<PipelineTemplate> templates;
  final bool isLoading;

  const TemplatesState({this.templates = const [], this.isLoading = true});

  TemplatesState copyWith({List<PipelineTemplate>? templates, bool? isLoading}) {
    return TemplatesState(
      templates: templates ?? this.templates,
      isLoading: isLoading ?? this.isLoading,
    );
  }

  @override
  List<Object?> get props => [templates, isLoading];
}

class TemplatesCubit extends Cubit<TemplatesState> {
  final ApiService api;

  TemplatesCubit(this.api) : super(const TemplatesState()) {
    fetchTemplates();
  }

  Future<void> fetchTemplates() async {
    try {
      final data = await api.getTemplates();
      final templates = data.map((e) => PipelineTemplate.fromJson(e as Map<String, dynamic>)).toList();
      if (!isClosed) emit(state.copyWith(templates: templates, isLoading: false));
    } catch (e, st) {
      log('Failed to fetch templates: $e', stackTrace: st, name: 'TemplatesCubit');
      if (!isClosed) emit(state.copyWith(isLoading: false));
    }
  }
}
